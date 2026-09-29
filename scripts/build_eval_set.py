import random
from collections import defaultdict
from pathlib import Path

import duckdb
import polars as pl


TARGET_PER_CLASS = 500
SEED = 42

LABEL_MAP = {
    "fastapi/fastapi": {
        "bug": "bug",
        "feature": "feature",
        "docs": "docs",
        "question": "question",
    },
    "kubernetes/kubernetes": {
        "kind/bug": "bug",
        "kind/feature": "feature",
        "kind/documentation": "docs",
        "kind/support": "question",
    },
    "microsoft/vscode": {
        "bug": "bug",
        "feature-request": "feature",
        "*question": "question",
    },
    "pytorch/pytorch": {
        "enhancement": "feature",
        "feature": "feature",
        "module: docs": "docs",
        "topic: docs": "docs",
    },
    "tensorflow/tensorflow": {
        "type:bug": "bug",
        "type:feature": "feature",
        "type:docs-bug": "docs",
        "type:docs-feature": "docs",
        "type:support": "question",
    },
}


con = duckdb.connect("data/issueflow.duckdb", read_only=True)

rows = con.execute("""
SELECT
    repo,
    id,
    title,
    body,
    labels
FROM issues
""").fetchall()

con.close()

candidates = defaultdict(lambda: defaultdict(list))

for repo, issue_id, title, body, labels in rows:
    mapping = LABEL_MAP.get(repo)

    if mapping is None:
        continue

    mapped_classes = {
        mapping[label]
        for label in labels
        if label in mapping
    }
    
    if len(mapped_classes) != 1:
        continue

    human_type = next(iter(mapped_classes))

    candidates[human_type][repo].append(
        {
            "repo": repo,
            "issue_id": issue_id,
            "title": title,
            "body": body or "",
            "human_type": human_type,
        }
    )


rng = random.Random(SEED)
selected = []

for human_type in ["bug", "feature", "docs", "question"]:
    repo_groups = candidates[human_type]

    for issues in repo_groups.values():
        rng.shuffle(issues)

    repo_names = list(repo_groups.keys())

    class_rows = []

    while len(class_rows) < TARGET_PER_CLASS:
        added = False

        for repo in repo_names:
            issues = repo_groups[repo]

            if not issues:
                continue

            class_rows.append(issues.pop())
            added = True

            if len(class_rows) >= TARGET_PER_CLASS:
                break

        if not added:
            break

    selected.extend(class_rows)

    print(
        f"{human_type}: "
        f"{len(class_rows)}/{TARGET_PER_CLASS}"
    )


df = pl.DataFrame(selected)

output = Path("data/eval.parquet")
df.write_parquet(output)

print(f"\nsaved {df.height} rows to {output}")

print("\nBy class:")
print(
    df.group_by("human_type")
    .len()
    .sort("human_type")
)

print("\nBy repo and class:")
print(
    df.group_by(["repo", "human_type"])
    .len()
    .sort(["human_type", "repo"])
)