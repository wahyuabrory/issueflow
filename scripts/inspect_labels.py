import duckdb

con = duckdb.connect("data/issueflow.duckdb")

repos = con.execute("""
SELECT DISTINCT repo
FROM issues
ORDER BY repo
""").fetchall()

for (repo,) in repos:
    print(f"\n{repo}")

    rows = con.execute("""
        SELECT label, COUNT(*) AS n
        FROM issues,
        UNNEST(labels) AS t(label)
        WHERE repo = ?
        GROUP BY label
        ORDER BY n DESC
        LIMIT 20
    """, [repo]).fetchall()

    for row in rows:
        print(row)

con.close()