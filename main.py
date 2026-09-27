import os

import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ["TYPESAFE_API_KEY"]

payload = {
    "model": "jev-latest",
    "state": {
        "title": "FastAPI crashes when uploading a large file",
        "body": "Uploading a large file causes an internal server error.",
    },
    "questions": {
        "issue_type": {
            "type": "choice",
            "instructions": "Classify this GitHub issue.",
            "criteria": {
                "bug": "Broken or incorrect behavior",
                "feature": "Request for new functionality",
                "docs": "Documentation issue",
                "question": "Request for help or information",
                "other": "Anything else",
            },
        }
    },
}

response = httpx.post(
    "https://api.typesafe.ai/v1/systemone",
    headers={"Authorization": f"Bearer {api_key}"},
    json=payload,
    timeout=30,
)

print(response.status_code)
print(response.json())