import duckdb

con = duckdb.connect("data/issueflow.duckdb")

con.execute("""
CREATE OR REPLACE TABLE issues AS
SELECT *
FROM read_parquet('data/issues.parquet')
""")

print(
  con.execute(
    """
    SELECT repo, COUNT(*) AS n
    FROM issues
    GROUP BY repo
    ORDER BY n DESC
    """
  ).fetchall()
)

con.close()