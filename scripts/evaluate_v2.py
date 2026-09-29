import duckdb

con = duckdb.connect("data/issueflow.duckdb")

rows = con.execute("""
SELECT
    e.human_type,
    p.predicted_type,
    COUNT(*) AS n
FROM read_parquet('data/eval.parquet') e
JOIN eval_predictions_v2 p
    ON e.issue_id = p.issue_id
GROUP BY 1, 2
ORDER BY 1, 2
""").fetchall()

classes = ["bug", "feature", "docs", "question"]

matrix = {
    actual: {pred: 0 for pred in classes + ["other"]}
    for actual in classes
}

for actual, predicted, n in rows:
    matrix[actual][predicted] = n

print("\nConfusion matrix")
print("actual -> predicted")

for actual in classes:
    print(actual, matrix[actual])

total = sum(
    sum(matrix[actual].values())
    for actual in classes
)

correct = sum(
    matrix[c][c]
    for c in classes
)

print(f"\nAccuracy: {correct}/{total} = {correct / total:.1%}")

print("\nPer-class metrics")

for c in classes:
    tp = matrix[c][c]

    fp = sum(
        matrix[actual][c]
        for actual in classes
        if actual != c
    )

    fn = sum(
        matrix[c][pred]
        for pred in matrix[c]
        if pred != c
    )

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0
    )

    print(
        f"{c}: "
        f"precision={precision:.3f} "
        f"recall={recall:.3f} "
        f"f1={f1:.3f}"
    )

tokens = con.execute("""
SELECT
    SUM(input_tokens),
    AVG(input_tokens)
FROM eval_predictions_v2
""").fetchone()

if tokens is None or tokens[0] is None or tokens[1] is None:
    raise RuntimeError("No evaluation predictions found")

total_tokens, avg_tokens = tokens

print(f"\nTotal input tokens: {total_tokens}")
print(f"Average input tokens: {avg_tokens:.1f}")

con.close()
