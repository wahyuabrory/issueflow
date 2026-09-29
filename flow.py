import subprocess

from prefect import flow, task

@task(retries=2)

def ingest():
    subprocess.run(["uv", "run", "ingest.py"], check=True)


@task
def transform():
    subprocess.run(["uv", "run", "transform.py"], check=True)


@task
def load():
    subprocess.run(["uv", "run", "load.py"], check=True)


@task(retries=2)
def classify():
    subprocess.run(["uv", "run", "classify.py"], check=True)


@task
def evaluate():
    subprocess.run(["uv", "run", "evaluate.py"], check=True)


@flow(name="issueflow")
def pipeline():
    ingest()
    transform()
    load()
    classify()
    evaluate()


if __name__ == "__main__":
    pipeline()