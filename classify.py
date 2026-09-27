import os
import duckdb
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ["TYPESAFE_API_KEY"]

con = duckdb.connect("data/issueflow.duckdb")

issues = con.execute("""
SELECT i.id, i.title, i.body
FROM issues i
LEFT JOIN classifications c
    ON i.id = c.issue_id
WHERE c.issue_id IS NULL
LIMIT 100
""").fetchall()

con.execute("""
CREATE TABLE IF NOT EXISTS classifications (
    issue_id BIGINT,
    issue_type VARCHAR,
    confidence DOUBLE
)
""")

for issue_id, title, body in issues:
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
        "INSERT INTO classifications VALUES (?, ?, ?)",
        [issue_id, answer["choice"], answer["confidence"]],
    )

    print(issue_id, answer["choice"], answer["confidence"])

con.close()