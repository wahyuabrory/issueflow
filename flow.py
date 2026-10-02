import subprocess
from time import perf_counter

from prefect import flow, get_run_logger, task


def run_stage(name, script):
    logger = get_run_logger()
    started = perf_counter()

    logger.info("%s started", name)

    try:
        subprocess.run(
            ["uv", "run", f"src/issueflow/{script}"],
            check=True,
        )
    except subprocess.CalledProcessError:
        duration = perf_counter() - started
        logger.exception("%s failed duration=%.2fs", name, duration)
        raise

    duration = perf_counter() - started
    logger.info("%s completed duration=%.2fs", name, duration)


@task(retries=2)
def ingest():
    run_stage("ingest", "ingest.py")


@task
def transform():
    run_stage("transform", "transform.py")


@task
def load():
    run_stage("load", "load.py")


@task(retries=2)
def classify():
    run_stage("classify", "classify.py")


@task
def quality():
    run_stage("quality", "quality.py")


@task
def evaluate():
    run_stage("evaluate", "evaluate.py")


@task
def analytics():
    run_stage("analytics", "analytics.py")


@flow(name="issueflow")
def pipeline():
    ingest()
    transform()
    load()
    classify()
    quality()
    evaluate()
    analytics()


if __name__ == "__main__":
    pipeline()