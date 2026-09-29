import subprocess

from prefect import flow, task

@task(retries=2)

def ingest():
    subprocess.run(["uv", "run", "src/issueflow/ingest.py"], check=True)


@task
def transform():
    subprocess.run(["uv", "run", "src/issueflow/transform.py"], check=True)


@task
def load():
    subprocess.run(["uv", "run", "src/issueflow/load.py"], check=True)


@task(retries=2)
def classify():
    subprocess.run(["uv", "run", "src/issueflow/classify.py"], check=True)


@task
def evaluate():
    subprocess.run(["uv", "run", "src/issueflow/evaluate.py"], check=True)


@task
def analytics():
    subprocess.run(["uv", "run", "src/issueflow/analytics.py"], check=True)


@flow(name="issueflow")
def pipeline():
    ingest()
    transform()
    load()
    classify()
    evaluate()
    analytics()

if __name__ == "__main__":
    pipeline()
