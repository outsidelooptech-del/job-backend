import requests
import json
import time

# =========================================
# ADD COMPANY BOARD NAMES HERE
# =========================================

boards = [
    "razorpay",
    "rippling",
    "coinbase",
    "canva",
    "atlassian",
    "twilio",
    "datadog",
    "snowflake",
    "plaid",
    "dropbox",
    "asana",
    "brex",
    "hashicorp",
    "snyk",
    "elastic",
    "mongodb",
    "purestorage",
    "confluent",
    "nutanix",
    "rubrik",
    "figma",
    "notion",
    "grammarly",
    "postman",
    "miro",
    "coursera",
    "webflow",
    "clickhouse",
    "robinhood",
    "yelp",
    "instacart",
    "rokt",
    "drata",
    "deel",
    "openai"
]

# =========================================
# CONFIG
# =========================================

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

valid_sources = []

print("🚀 Checking Greenhouse boards...\n")

# =========================================
# CHECK BOARDS
# =========================================

for board in boards:

    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        status = response.status_code

        if status == 200:

            data = response.json()
            jobs = data.get("jobs", [])

            print(f"✅ {board} | Jobs: {len(jobs)}")

            valid_sources.append({
                "company": board.title(),
                "ats": "greenhouse",
                "board": board
            })

        else:
            print(f"❌ {board} | Status: {status}")

    except Exception as e:
        print(f"⚠️ {board} | Error: {e}")

    time.sleep(0.5)

# =========================================
# SAVE VALID SOURCES
# =========================================

with open(
    "valid_greenhouse_sources.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        valid_sources,
        f,
        indent=4,
        ensure_ascii=False
    )

print("\n🎯 Total valid boards:", len(valid_sources))
print("📂 Saved to valid_greenhouse_sources.json")