import duckdb

con = duckdb.connect("data/issueflow.duckdb")

con.execute("""
CREATE OR REPLACE TABLE issues AS
SELECT *
FROM read_parquet('data/issues.parquet')
""")

result = con.execute("""
SELECT state, COUNT(*) AS count
FROM issues
GROUP BY state
""").fetchall()

print(result)

con.close()