import duckdb

con = duckdb.connect("data/issueflow.duckdb")

rows = con.execute("""
SELECT
    g.gold_label,
    p.predicted_type,
    p.confidence,
    g.repo,
    g.title
FROM read_csv_auto('data/gold_dev.csv') g
JOIN eval_predictions_v2 p
    ON g.issue_id = p.issue_id
WHERE g.gold_label != p.predicted_type
ORDER BY p.confidence DESC
""").fetchall()

print(f"errors: {len(rows)}")

for row in rows:
    print(row)

con.close()