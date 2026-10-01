import duckdb

con = duckdb.connect("data/issueflow.duckdb")

rows = con.execute("""
SELECT
    e.human_type,
    p.predicted_type,
    p.confidence,
    e.repo,
    e.title
FROM read_parquet('data/eval.parquet') e
JOIN eval_predictions_v2 p
    ON e.issue_id = p.issue_id
WHERE e.human_type != p.predicted_type
ORDER BY p.confidence DESC
LIMIT 50
""").fetchall()

for row in rows:
    print(row)

con.close()