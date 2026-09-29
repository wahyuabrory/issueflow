import json
import os
from pathlib import Path

import duckdb
import httpx
from dotenv import load_dotenv

load_dotenv()

token = os.environ["GITHUB_TOKEN"]
raw_path = Path("data/raw/issues.json")

con = duckdb.connect("data/issueflow.duckdb", read_only=True)
row = con.execute("""
SELECT MAX(updated_at)
FROM issues
""").fetchone()

con.close()

if row is None or row[0] is None:
    raise RuntimeError("No watermark found in issues table")

since = row[0]

print(f"since: {since}")

updates = []
page = 1

while True:
    response = httpx.get(
        "https://api.github.com/repos/fastapi/fastapi/issues",
        params={
            "state": "all",
            "per_page": 100,
            "page": page,
            "since": since,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
    )

    response.raise_for_status()
    batch = response.json()

    if not batch:
        break

    updates.extend(
        item for item in batch
        if "pull_request" not in item
    )

    page += 1

print(f"found {len(updates)} updated issues")
with raw_path.open() as f:
    existing = json.load(f)

merged = {issue["id"]: issue for issue in existing}

for issue in updates:
    merged[issue["id"]] = issue

with raw_path.open("w") as f:
    json.dump(list(merged.values()), f, indent=2)

print(f"total stored issues: {len(merged)}")
