import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

token = os.environ["GITHUB_TOKEN"]

issues = []
page = 1
target = 500
while len(issues) < target:
    response = httpx.get(
        "https://api.github.com/repos/fastapi/fastapi/issues",
        params={
            "state": "all",
            "per_page": 100,
            "page": page,
        },
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
    )

    response.raise_for_status()

    batch = response.json()

    if not batch:
        break

    issues.extend(
        item for item in batch
        if "pull_request" not in item
    )

    print(f"page {page}: {len(issues)} issues collected")
    page += 1

issues = issues[:target]

Path("data/raw").mkdir(parents=True, exist_ok=True)

with open("data/raw/issues.json", "w") as f:
    json.dump(issues, f, indent=2)

print(f"saved {len(issues)} issues")