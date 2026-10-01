import duckdb

CLASSES = ["bug", "feature", "docs", "question", "other"]

con = duckdb.connect("data/issueflow.duckdb")

rows = con.execute("""
SELECT
    g.gold_label,
    p.predicted_type,
    COUNT(*) AS n
FROM read_csv_auto('data/gold_test.csv') g
JOIN eval_predictions_v2 p
    ON g.issue_id = p.issue_id
GROUP BY 1, 2
ORDER BY 1, 2
""").fetchall()

con.close()

matrix = {
    actual: {pred: 0 for pred in CLASSES}
    for actual in CLASSES
}

for actual, predicted, count in rows:
    matrix[actual][predicted] = count

print("\nConfusion matrix")

for actual in CLASSES:
    print(actual, matrix[actual])

total = sum(sum(row.values()) for row in matrix.values())
correct = sum(matrix[c][c] for c in CLASSES)

print(f"\nAccuracy: {correct}/{total} = {correct / total:.1%}")

print("\nPer-class metrics")

f1_scores = []

for c in CLASSES:
    tp = matrix[c][c]

    fp = sum(
        matrix[actual][c]
        for actual in CLASSES
        if actual != c
    )

    fn = sum(
        matrix[c][pred]
        for pred in CLASSES
        if pred != c
    )

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0
    )

    f1_scores.append(f1)

    print(
        f"{c}: "
        f"precision={precision:.3f} "
        f"recall={recall:.3f} "
        f"f1={f1:.3f}"
    )

print(f"\nMacro F1: {sum(f1_scores) / len(f1_scores):.3f}")