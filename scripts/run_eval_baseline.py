import os
import time

import duckdb
import httpx
import polars as pl
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ["TYPESAFE_API_KEY"]

df = pl.read_parquet("data/eval.parquet")

con = duckdb.connect("data/issueflow.duckdb")

con.execute("""
CREATE TABLE IF NOT EXISTS eval_predictions (
    issue_id BIGINT PRIMARY KEY,
    predicted_type VARCHAR,
    confidence DOUBLE,
    input_tokens INTEGER
)
""")

existing = {
    row[0]
    for row in con.execute(
        "SELECT issue_id FROM eval_predictions"
    ).fetchall()
}

with httpx.Client(timeout=30) as client:
    for i, row in enumerate(df.iter_rows(named=True), start=1):
        issue_id = row["issue_id"]

        if issue_id in existing:
            continue

        payload = {
            "model": "jev-latest",
            "state": {
                "title": row["title"],
                "body": row["body"][:4000],
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

        response = client.post(
            "https://api.typesafe.ai/v1/systemone",
            headers={
                "Authorization": f"Bearer {api_key}"
            },
            json=payload,
        )

        response.raise_for_status()
        result = response.json()

        answer = result["answers"]["issue_type"]
        tokens = result["usage"]["input_tokens"]

        con.execute(
            """
            INSERT INTO eval_predictions
            VALUES (?, ?, ?, ?)
            """,
            [
                issue_id,
                answer["choice"],
                answer["confidence"],
                tokens,
            ],
        )

        if i % 50 == 0:
            print(f"{i}/2000")

        time.sleep(0.05)

con.close()