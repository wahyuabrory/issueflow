import duckdb

con = duckdb.connect("data/issueflow.duckdb")

rows = con.execute("""
WITH human AS (
    SELECT
        id,
        CASE
            WHEN labels = ['bug'] THEN 'bug'
            WHEN labels = ['question'] THEN 'question'
            WHEN labels = ['feature'] THEN 'feature'
            WHEN labels = ['docs'] THEN 'docs'
        END AS human_type
    FROM issues
)
SELECT
    h.human_type,
    c.issue_type AS jev_type,
    COUNT(*) AS n
FROM human h
JOIN classifications c
    ON h.id = c.issue_id
WHERE h.human_type IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 3 DESC
""").fetchall()

for row in rows:
    print(row)

total = sum(row[2] for row in rows)
correct = sum(row[2] for row in rows if row[0] == row[1])

print(f"\nAgreement: {correct}/{total} = {correct / total:.1%}")

con.close()
