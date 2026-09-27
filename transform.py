import json

import polars as pl

with open("data/raw/issues.json") as f:
    raw = json.load(f)

df = pl.DataFrame(
    {
        "id": [x["id"] for x in raw],
        "number": [x["number"] for x in raw],
        "title": [x["title"] for x in raw],
        "body": [x["body"] or "" for x in raw],
        "state": [x["state"] for x in raw],
        "created_at": [x["created_at"] for x in raw],
        "closed_at": [x["closed_at"] for x in raw],
        "labels": [[label["name"] for label in x["labels"]] for x in raw],
    }
)

df.write_parquet("data/issues.parquet")

print(df.head())
print(f"saved {df.height} rows")