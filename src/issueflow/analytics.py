import duckdb

con = duckdb.connect("data/issueflow.duckdb")

CLASSIFIER_VERSION = "v2"

total_row = con.execute("""
    SELECT COUNT(*)
    FROM issues
""").fetchone()

total_issues = int(total_row[0]) if total_row is not None else 0

classified_row = con.execute("""
    SELECT COUNT(*)
    FROM classifications
    WHERE classifier_version = ?
""", [CLASSIFIER_VERSION]).fetchone()

classified_issues = (
    int(classified_row[0])
    if classified_row is not None
    else 0
)

coverage = (
    classified_issues / total_issues * 100
    if total_issues
    else 0.0
)

print("\nClassification coverage")
print(
    f"{classified_issues:,} / {total_issues:,} "
    f"({coverage:.2f}%)"
)

usage = con.execute("""
    SELECT
        COALESCE(SUM(input_tokens), 0),
        COALESCE(SUM(estimated_cost_usd), 0)
    FROM classification_usage
    WHERE classifier_version = ?
""", [CLASSIFIER_VERSION]).fetchone()

if usage is not None:
    total_tokens = int(usage[0])
    total_cost = float(usage[1])
else:
    total_tokens = 0
    total_cost = 0.0

print("\nToken usage")
print(f"{total_tokens:,}")

print("\nEstimated cost")
print(f"${total_cost:.4f}")

print("\nIssue count by class")
print(
    con.execute("""
        SELECT issue_type, COUNT(*) AS n
        FROM classifications
        WHERE classifier_version = ?
        GROUP BY issue_type
        ORDER BY n DESC
    """, [CLASSIFIER_VERSION]).fetchall()
)

print("\nAverage confidence by class")
print(
    con.execute("""
        SELECT
            issue_type,
            ROUND(AVG(confidence), 3) AS avg_confidence
        FROM classifications
        WHERE classifier_version = ?
        GROUP BY issue_type
        ORDER BY avg_confidence DESC
    """, [CLASSIFIER_VERSION]).fetchall()
)

print("\nOpen vs Closed")
print(
    con.execute("""
        SELECT state, COUNT(*) AS n
        FROM issues
        GROUP BY state
        ORDER BY n DESC
    """).fetchall()
)

low_confidence_row = con.execute("""
    SELECT COUNT(*)
    FROM classifications
    WHERE classifier_version = ?
      AND confidence < 0.6
""", [CLASSIFIER_VERSION]).fetchone()

low_confidence_count = (
    int(low_confidence_row[0])
    if low_confidence_row is not None
    else 0
)

print("\nLow-confidence predictions")
print(f"Count: {low_confidence_count:,}")

print("\nLowest-confidence examples")
print(
    con.execute("""
        SELECT
            i.number,
            i.title,
            c.issue_type,
            c.confidence
        FROM classifications c
        JOIN issues i
            ON c.issue_id = i.id
        WHERE c.classifier_version = ?
          AND c.confidence < 0.6
        ORDER BY c.confidence ASC
        LIMIT 10
    """, [CLASSIFIER_VERSION]).fetchall()
)

con.close()