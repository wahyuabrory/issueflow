import sys
import duckdb


DB_PATH = "data/issueflow.duckdb"
CLASSIFIER_VERSION = "v2"

con = duckdb.connect(DB_PATH)


def scalar(query, params=None):
    row = con.execute(query, params or []).fetchone()
    return int(row[0]) if row is not None else 0


checks = [
    (
        "Duplicate issue IDs",
        """
        SELECT COUNT(*)
        FROM (
            SELECT id
            FROM issues
            GROUP BY id
            HAVING COUNT(*) > 1
        )
        """,
    ),
    (
        "Missing required issue fields",
        """
        SELECT COUNT(*)
        FROM issues
        WHERE id IS NULL
           OR repo IS NULL
           OR number IS NULL
           OR title IS NULL
           OR state IS NULL
           OR created_at IS NULL
           OR updated_at IS NULL
        """,
    ),
    (
        "Invalid issue states",
        """
        SELECT COUNT(*)
        FROM issues
        WHERE state NOT IN ('open', 'closed')
           OR state IS NULL
        """,
    ),
    (
        "Classification IDs missing from issues",
        """
        SELECT COUNT(*)
        FROM classifications c
        LEFT JOIN issues i
            ON c.issue_id = i.id
        WHERE i.id IS NULL
        """,
    ),
    (
        "Duplicate classification issue IDs",
        """
        SELECT COUNT(*)
        FROM (
            SELECT issue_id
            FROM classifications
            GROUP BY issue_id
            HAVING COUNT(*) > 1
        )
        """,
    ),
    (
        "Invalid V2 classes",
        """
        SELECT COUNT(*)
        FROM classifications
        WHERE classifier_version = ?
          AND (
              issue_type NOT IN (
                  'bug',
                  'feature',
                  'docs',
                  'question',
                  'other'
              )
              OR issue_type IS NULL
          )
        """,
    ),
    (
        "Invalid V2 confidence values",
        """
        SELECT COUNT(*)
        FROM classifications
        WHERE classifier_version = ?
          AND (
              confidence < 0
              OR confidence > 1
              OR confidence IS NULL
          )
        """,
    ),
    (
        "Stale V2 classifications",
        """
        SELECT COUNT(*)
        FROM classifications c
        JOIN issues i
            ON c.issue_id = i.id
        WHERE c.classifier_version = ?
          AND c.issue_updated_at IS DISTINCT FROM i.updated_at
        """,
    ),
]

failed = 0

print("Data quality checks")

for name, query in checks:
    params = [CLASSIFIER_VERSION] if "?" in query else []
    count = scalar(query, params)

    if count == 0:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}: {count:,}")
        failed += 1

total_issues = scalar("""
    SELECT COUNT(*)
    FROM issues
""")

classified = scalar("""
    SELECT COUNT(*)
    FROM classifications
    WHERE classifier_version = ?
""", [CLASSIFIER_VERSION])

coverage = classified / total_issues * 100 if total_issues else 0.0

print()
print("Classification coverage")
print(f"{classified:,} / {total_issues:,} ({coverage:.2f}%)")

con.close()

if failed:
    print()
    print(f"Quality checks failed: {failed}")
    sys.exit(1)

print()
print("All quality checks passed")