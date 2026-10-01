import duckdb

CLASSES = ["bug", "feature", "docs", "question", "other"]

con = duckdb.connect("data/issueflow.duckdb")

for table in ["eval_predictions_v2", "eval_predictions_v3"]:
    rows = con.execute(f"""
    SELECT
        g.gold_label,
        p.predicted_type,
        COUNT(*) AS n
    FROM read_csv_auto('data/gold_dev.csv') g
    JOIN {table} p
        ON g.issue_id = p.issue_id
    GROUP BY 1, 2
    ORDER BY 1, 2
    """).fetchall()

    matrix = {
        actual: {pred: 0 for pred in CLASSES}
        for actual in CLASSES
    }

    for actual, predicted, n in rows:
        matrix[actual][predicted] = n

    total = sum(sum(x.values()) for x in matrix.values())
    correct = sum(matrix[c][c] for c in CLASSES)

    f1_scores = []

    print(f"\n{table}")
    print(f"accuracy: {correct}/{total} = {correct / total:.1%}")

    for c in CLASSES:
        tp = matrix[c][c]
        fp = sum(matrix[a][c] for a in CLASSES if a != c)
        fn = sum(matrix[c][p] for p in CLASSES if p != c)

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

    print(f"macro_f1: {sum(f1_scores) / len(f1_scores):.3f}")

con.close()