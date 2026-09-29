import duckdb

con = duckdb.connect("data/issueflow.duckdb")

rows = con.execute("""
SELECT
    repo,
    label,
    COUNT(*) AS n
FROM issues,
UNNEST(labels) AS t(label)
WHERE
    lower(label) LIKE '%bug%'
    OR lower(label) LIKE '%feature%'
    OR lower(label) LIKE '%enhance%'
    OR lower(label) LIKE '%doc%'
    OR lower(label) LIKE '%support%'
    OR lower(label) LIKE '%question%'
GROUP BY repo, label
ORDER BY repo, n DESC
""").fetchall()

current_repo = None

for repo, label, count in rows:
    if repo != current_repo:
        print(f"\n{repo}")
        current_repo = repo

    print(label, count)

con.close()