import duckdb
import polars as pl

con = duckdb.connect("data/issueflow.duckdb", read_only=True)

rows = con.execute("""
WITH ranked AS (
    SELECT
        e.issue_id,
        e.repo,
        i.number,
        e.title,
        e.body,
        i.labels AS github_labels,
        e.human_type AS weak_label,
        p.predicted_type AS jev_v2_prediction,
        p.confidence,
        ROW_NUMBER() OVER (
            PARTITION BY e.human_type
            ORDER BY HASH(e.issue_id)
        ) AS rn
    FROM read_parquet('data/eval.parquet') e
    JOIN issues i
        ON e.issue_id = i.id
    JOIN eval_predictions_v2 p
        ON e.issue_id = p.issue_id
)
SELECT
    issue_id,
    repo,
    number,
    title,
    body,
    github_labels,
    weak_label,
    jev_v2_prediction,
    confidence
FROM ranked
WHERE rn <= 100
ORDER BY weak_label, repo, issue_id
""").fetchall()

con.close()

df = pl.DataFrame(
    rows,
    schema=[
        "issue_id",
        "repo",
        "number",
        "title",
        "body",
        "github_labels",
        "weak_label",
        "jev_v2_prediction",
        "confidence",
    ],
    orient="row",
)

df = df.with_columns(
    pl.col("github_labels")
    .list.join("|")
    .alias("github_labels"),

    pl.lit("").alias("gold_label"),
)

df.write_csv("data/gold_review.csv")

print(f"saved {df.height} issues")
print(df.group_by("weak_label").len())