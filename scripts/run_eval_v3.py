import os
import time

import duckdb
import httpx
import polars as pl
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ["TYPESAFE_API_KEY"]

df = pl.read_csv("data/gold_dev.csv")

con = duckdb.connect("data/issueflow.duckdb")

con.execute("""
CREATE TABLE IF NOT EXISTS eval_predictions_v3 (
    issue_id BIGINT PRIMARY KEY,
    predicted_type VARCHAR,
    confidence DOUBLE,
    input_tokens INTEGER
)
""")

existing = {
    row[0] for row in con.execute("SELECT issue_id FROM eval_predictions_v3").fetchall()
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
                            "The issue reports broken, incorrect, failing, crashing, regressed, "
                            "or unexpectedly missing behavior in the software. Choose bug when "
                            "the issue describes a concrete failure or behavior that should work "
                            "but does not, even if the author asks for help."
                        ),
                        "feature": (
                            "The issue requests a new capability, behavior, option, optimization, "
                            "or improvement that does not currently exist."
                        ),
                        "docs": (
                            "The primary issue is missing, incorrect, unclear, outdated, or "
                            "misleading documentation, examples, tutorials, or API documentation."
                        ),
                        "question": (
                            "The primary intent is to ask how, why, whether, or how to configure "
                            "or use something. Choose question only when there is no clear evidence "
                            "of broken or incorrect software behavior."
                        ),
                        "other": (
                            "The issue does not clearly fit bug, feature, docs, or question."
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
            INSERT INTO eval_predictions_v3
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
            print(f"{i}/{df.height}")

        time.sleep(0.05)

con.close()
