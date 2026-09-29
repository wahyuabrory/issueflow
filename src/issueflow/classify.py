import os
import duckdb
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ["TYPESAFE_API_KEY"]

con = duckdb.connect("data/issueflow.duckdb")

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
   OR c.issue_updated_at != i.updated_at
""").fetchall()

con.execute("""
CREATE TABLE IF NOT EXISTS classifications (
    issue_id BIGINT,
    issue_type VARCHAR,
    confidence DOUBLE
)
""")

for issue_id, title, body, updated_at in issues:
    payload = {
        "model": "jev-latest",
        "state": {
            "title": title,
            "body": body[:4000],
        },
        "questions": {
            "issue_type": {
                "type": "choice",
                "instructions": "Classify this GitHub issue.",
                "criteria": {
                    "bug": "Broken or incorrect behavior",
                    "feature": "Request for new functionality",
                    "docs": "Documentation issue",
                    "question": "Request for help or information",
                    "other": "Anything else",
                },
            }
        },
    }

    response = httpx.post(
        "https://api.typesafe.ai/v1/systemone",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    answer = response.json()["answers"]["issue_type"]

    con.execute(
        "DELETE FROM classifications WHERE issue_id = ?",
        [issue_id],
    )

    con.execute(
        """
        INSERT INTO classifications (
            issue_id,
            issue_type,
            confidence,
            issue_updated_at
        )
        VALUES (?, ?, ?, ?)
        """,
        [
            issue_id,
            answer["choice"],
            answer["confidence"],
            updated_at,
        ],
    )

    print(issue_id, answer["choice"], answer["confidence"])

con.close()
