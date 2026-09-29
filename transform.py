import json
from pathlib import Path

import polars as pl

raw_root = Path("data/raw")

rows = []

for path in raw_root.glob("*/*.json"):
  repo = path.parent.name.replace("_", "/", 1)

  with path.open() as f:
    issues = json.load(f)

  for issue in issues:
    rows.append(
        {
            "id": issue["id"],
            "repo": repo,
            "number": issue["number"],
            "title": issue["title"],
            "body": issue["body"] or "",
            "state": issue["state"],
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"],
            "closed_at": issue["closed_at"],
            "labels": [label["name"] for label in issue["labels"]],
        }
    )
df = pl.DataFrame(rows)

Path("data").mkdir(exist_ok=True)

df.write_parquet("data/issues.parquet")

print(df.head())
print(f"saved {df.height} rows")
print(df.group_by("repo").len())