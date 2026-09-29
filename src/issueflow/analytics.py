import duckdb

con = duckdb.connect("data/issueflow.duckdb")

print("\nIssue count by class")
print(
  con.execute("""
    SELECT issue_type, COUNT(*) AS n
    FROM classifications
    GROUP BY issue_type
    ORDER BY n DESC
    """).fetchall()
)

print("\nAverage confidence by class")
print(
  con.execute(
    """
    SELECT 
      issue_type,
      ROUND(AVG(confidence), 3) AS avg_confidence
    FROM classifications
    GROUP BY issue_type
    ORDER BY avg_confidence DESC
    """
  ).fetchall()
)

print("\nOpen vs Closed")
print(
  con.execute("""
    SELECT state, COUNT(*) AS n
    FROM issues
    GROUP BY state
    ORDER BY n DESC
    """
  ).fetchall()
)

print("\nLow-confidence predictions")
print(
  con.execute(
    """
    SELECT
      i.number,
      i.title,
      c.issue_type,
      c.confidence,
    FROM classifications c
    JOIN issues i
      ON c.issue_id = i.id
    WHERE c.confidence < 0.6
    ORDER BY c.confidence DESC
    """
  ).fetchall()
)

con.close()