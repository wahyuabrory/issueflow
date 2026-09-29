import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

token = os.environ["GITHUB_TOKEN"]

REPO_LIMITS = {
  "fastapi/fastapi": 4_000,
  "microsoft/vscode": 50_000,
  "kubernetes/kubernetes": 20_000,
  "pytorch/pytorch": 20_000,
  "tensorflow/tensorflow": 20_000,
}

TARGET = 100_000
raw_root = Path("data/raw")

QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issues(
      first: 100
      after: $cursor
      orderBy: {field: CREATED_AT, direction: DESC}
    ) {
      nodes {
        databaseId
        number
        title
        body
        state
        createdAt
        updatedAt
        closedAt
        labels(first: 50) {
          nodes {
            name
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }

  rateLimit {
    cost
    remaining
    resetAt
  }
}
"""


def existing_ids(repo_dir: Path) -> set[int]:
  ids = set()

  for path in repo_dir.glob("*.json"):
    with path.open() as f:
      for issue in json.load(f):
        ids.add(issue["id"])

  return ids


total = 0

for repo in REPO_LIMITS:
  repo_dir = raw_root / repo.replace("/", "_")

  if repo_dir.exists():
    total += len(existing_ids(repo_dir))

print(f"starting with {total}/{TARGET} existing issues")

headers = {
  "Authorization": f"Bearer {token}",
}

with httpx.Client(headers=headers, timeout=60) as client:
  for repo, repo_limit in REPO_LIMITS.items():
    if total >= TARGET:
      break

    owner, name = repo.split("/")

    repo_dir = raw_root / repo.replace("/", "_")
    repo_dir.mkdir(parents=True, exist_ok=True)

    seen = existing_ids(repo_dir)
    repo_count = len(seen)

    print(
      f"\n{repo}: "
      f"{repo_count}/{repo_limit} existing"
    )

    if repo_count >= repo_limit:
        print(f"{repo}: already have {repo_count}, skipping")

    cursor = None
    page = 1

    while total < TARGET and repo_count < repo_limit:
      response = client.post(
        "https://api.github.com/graphql",
        json={
          "query": QUERY,
          "variables": {
            "owner": owner,
            "name": name,
            "cursor": cursor,
          },
        },
      )

      response.raise_for_status()
      payload = response.json()

      if "errors" in payload:
        raise RuntimeError(payload["errors"])

      data = payload["data"]
      connection = data["repository"]["issues"]

      issues = []

      for node in connection["nodes"]:
        issue_id = node["databaseId"]

        if issue_id in seen:
          continue

        issues.append(
          {
            "id": issue_id,
            "number": node["number"],
            "title": node["title"],
            "body": node["body"] or "",
            "state": node["state"].lower(),
            "created_at": node["createdAt"],
            "updated_at": node["updatedAt"],
            "closed_at": node["closedAt"],
            "labels": [
              {"name": label["name"]}
              for label in node["labels"]["nodes"]
            ],
          }
        )

      global_remaining = TARGET - total
      repo_remaining = repo_limit - repo_count

      issues = issues[:min(global_remaining, repo_remaining)]

      if issues:
        start_index = repo_count

        output_path = (
          repo_dir / f"batch_{start_index:06d}.json"
        )

        with output_path.open("w") as f:
          json.dump(issues, f)

        new_ids = {
            issue["id"] for issue in issues
        }

        seen.update(new_ids)
        repo_count += len(issues)
        total += len(issues)

      rate = data["rateLimit"]

      print(
        f"{repo} page {page}: "
        f"repo={repo_count}/{repo_limit}, "
        f"total={total}/{TARGET}, "
        f"rate={rate['remaining']}"
      )

      page_info = connection["pageInfo"]

      if not page_info["hasNextPage"]:
        print(f"{repo}: no more issues")
        break

      cursor = page_info["endCursor"]
      page += 1

print(f"finished: {total}/{TARGET} issues")
