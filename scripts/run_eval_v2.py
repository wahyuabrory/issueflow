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
CREATE TABLE IF NOT EXISTS eval_predictions_v2 (
    issue_id BIGINT PRIMARY KEY,
    predicted_type VARCHAR,
    confidence DOUBLE,
    input_tokens INTEGER
)
""")

existing = {
    row[0] for row in con.execute("SELECT issue_id FROM eval_predictions_v2").fetchall()
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
                        "bug": (
                            "Reports a confirmed defect, regression, or behavior that is "
                            "clearly different from expected behavior. Do not choose bug "
                            "only because an error or failure is mentioned."
                        ),
                        "feature": (
                            "Requests new functionality, capability, behavior, or improvement."
                        ),
                        "docs": (
                            "Reports missing, incorrect, unclear, or outdated documentation, "
                            "or requests a documentation improvement."
                        ),
                        "question": (
                            "Primarily asks how, why, or whether something works, requests "
                            "help with usage or configuration, or describes a problem without "
                            "clearly proving that the software itself is defective."
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
        result = response.json()

        answer = result["answers"]["issue_type"]
        tokens = result["usage"]["input_tokens"]

        con.execute(
            """
            INSERT INTO eval_predictions_v2
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
