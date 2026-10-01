import polars as pl

SEED = 42

df = pl.read_csv("data/gold_review.csv")

dev_parts = []
test_parts = []

for label in ["bug", "feature", "docs", "question", "other"]:
    part = df.filter(pl.col("gold_label") == label)

    part = part.sample(
        fraction=1.0,
        shuffle=True,
        seed=SEED,
    )

    n = part.height
    test_n = max(1, round(n * 0.25))

    test_parts.append(part.head(test_n))
    dev_parts.append(part.slice(test_n))


dev = pl.concat(dev_parts)
test = pl.concat(test_parts)

dev.write_csv("data/gold_dev.csv")
test.write_csv("data/gold_test.csv")

print("dev:", dev.height)
print(dev.group_by("gold_label").len().sort("gold_label"))

print("\ntest:", test.height)
print(test.group_by("gold_label").len().sort("gold_label"))