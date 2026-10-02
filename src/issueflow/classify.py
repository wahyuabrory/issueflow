import os
import duckdb
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ["TYPESAFE_API_KEY"]
con = duckdb.connect("data/issueflow.duckdb")

MAX_RUN_COST_USD = 4.20
PRICE_PER_MILLION_INPUT_TOKENS = 0.042
BUDGET_RESERVE_USD = 0.02

CLASSIFIER_VERSION = "v2"
MODEL = "jev-latest"

MAX_ISSUES = None


con.execute("""
CREATE TABLE IF NOT EXISTS classifications (
    issue_id BIGINT,
    issue_type VARCHAR,
    confidence DOUBLE
)
""")

con.execute("""
ALTER TABLE classifications
ADD COLUMN IF NOT EXISTS issue_updated_at VARCHAR
""")

con.execute("""
ALTER TABLE classifications
ADD COLUMN IF NOT EXISTS input_tokens INTEGER
""")

con.execute("""
ALTER TABLE classifications
ADD COLUMN IF NOT EXISTS model VARCHAR
""")

con.execute("""
ALTER TABLE classifications
ADD COLUMN IF NOT EXISTS classifier_version VARCHAR
""")

con.execute("""
ALTER TABLE classifications
ADD COLUMN IF NOT EXISTS estimated_cost_usd DOUBLE
""")

con.execute("""
ALTER TABLE classifications
ADD COLUMN IF NOT EXISTS classified_at TIMESTAMP
""")

con.execute("""
CREATE TABLE IF NOT EXISTS classification_usage (
    issue_id BIGINT,
    classifier_version VARCHAR,
    model VARCHAR,
    input_tokens INTEGER,
    estimated_cost_usd DOUBLE,
    classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

row = con.execute("""
SELECT COALESCE(SUM(estimated_cost_usd), 0)
FROM classification_usage
WHERE classifier_version = ?
""", [CLASSIFIER_VERSION]).fetchone()

already_spent = float(row[0]) if row is not None else 0.0

print(f"Recorded V2 spend: ${already_spent:.4f}")
print(f"Budget limit:       ${MAX_RUN_COST_USD:.2f}")


issues = con.execute("""
SELECT
    i.id,
    i.title,
    i.body,
    i.updated_at
FROM issues i
LEFT JOIN classifications c
    ON i.id = c.issue_id
WHERE c.issue_id IS NULL
   OR c.issue_updated_at IS DISTINCT FROM i.updated_at
   OR c.classifier_version IS DISTINCT FROM ?
ORDER BY i.id
""", [CLASSIFIER_VERSION]).fetchall()

if MAX_ISSUES is not None:
    issues = issues[:MAX_ISSUES]

print(f"Issues to process: {len(issues)}")

session_tokens = 0
session_cost = 0.0
processed = 0


with httpx.Client(timeout=30) as client:
    for index, (issue_id, title, body, updated_at) in enumerate(
        issues,
        start=1,
    ):
        total_spent = already_spent + session_cost

        if total_spent >= MAX_RUN_COST_USD - BUDGET_RESERVE_USD:
            print(
                f"Budget stop: ${total_spent:.4f} spent "
                f"of ${MAX_RUN_COST_USD:.2f}"
            )
            break

        payload = {
            "model": MODEL,
            "state": {
                "title": title or "",
                "body": (body or "")[:4000],
            },
            "questions": {
                "issue_type": {
                    "type": "choice",
                    "instructions": "Classify this GitHub issue.",
                    "criteria": {
                        "bug": (
                            "Reports a confirmed defect, regression, or behavior "
                            "that is clearly different from expected behavior. "
                            "Do not choose bug only because an error or failure "
                            "is mentioned."
                        ),
                        "feature": (
                            "Requests new functionality, capability, behavior, "
                            "or improvement."
                        ),
                        "docs": (
                            "Reports missing, incorrect, unclear, or outdated "
                            "documentation, or requests a documentation improvement."
                        ),
                        "question": (
                            "Primarily asks how, why, or whether something works, "
                            "requests help with usage or configuration, or describes "
                            "a problem without clearly proving that the software "
                            "itself is defective."
                        ),
                        "other": (
                            "Does not clearly match bug, feature, docs, or question."
                        ),
                    },
                }
            },
        }

        response = client.post(
            "https://api.typesafe.ai/v1/systemone",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )

        response.raise_for_status()

        data = response.json()
        answer = data["answers"]["issue_type"]

        usage = data.get("usage", {})

        if "input_tokens" not in usage:
            raise RuntimeError(
                "Jev response did not contain usage.input_tokens"
            )

        input_tokens = int(usage["input_tokens"])

        cost = (
            input_tokens
            / 1_000_000
            * PRICE_PER_MILLION_INPUT_TOKENS
        )

        con.execute("""
        INSERT INTO classification_usage (
            issue_id,
            classifier_version,
            model,
            input_tokens,
            estimated_cost_usd
        )
        VALUES (?, ?, ?, ?, ?)
        """, [
            issue_id,
            CLASSIFIER_VERSION,
            MODEL,
            input_tokens,
            cost,
        ])

        con.execute(
            "DELETE FROM classifications WHERE issue_id = ?",
            [issue_id],
        )

        con.execute("""
        INSERT INTO classifications (
            issue_id,
            issue_type,
            confidence,
            issue_updated_at,
            input_tokens,
            model,
            classifier_version,
            estimated_cost_usd,
            classified_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [
            issue_id,
            answer["choice"],
            answer["confidence"],
            updated_at,
            input_tokens,
            MODEL,
            CLASSIFIER_VERSION,
            cost,
        ])

        session_tokens += input_tokens
        session_cost += cost
        processed += 1

        if index == 1 or index % 50 == 0:
            print(
                f"{index}/{len(issues)} "
                f"type={answer['choice']} "
                f"tokens={input_tokens} "
                f"session_cost=${session_cost:.4f}"
            )


if processed:
    average_tokens = session_tokens / processed

    projected_100k_cost = (
        average_tokens
        * 100_000
        / 1_000_000
        * PRICE_PER_MILLION_INPUT_TOKENS
    )

    print()
    print(f"Processed: {processed}")
    print(f"Input tokens: {session_tokens:,}")
    print(f"Average tokens/issue: {average_tokens:.1f}")
    print(f"Pilot cost: ${session_cost:.4f}")
    print(
        f"Projected 100k cost: "
        f"${projected_100k_cost:.2f}"
    )

con.close()