import requests
import json
import time
import os
import shutil

SOURCE_FILE = "internship_sources.json"
BACKUP_FILE = "internship_sources_backup.json"

boards = [
    "twilio", "datadog", "dropbox", "asana", "brex", "elastic",
    "mongodb", "purestorage", "rubrik", "figma", "postman",
    "coursera", "webflow", "clickhouse", "robinhood", "instacart",

    "cloudflare", "stripe", "airbnb", "databricks", "zscaler",
    "gitlab", "hubspot", "discord", "fivetran", "okta",
    "reddit", "twitch", "duolingo",

    "doordash", "affirm", "box", "lyft", "redditinc",
    "zapier", "vercel", "segment", "checkr", "benchling",
    "gusto", "samsara", "verkada", "mixpanel", "amplitude",
    "meraki", "wealthsimple", "navan", "outreach", "circleci",
    "loom", "airtable", "calendly", "braze", "klaviyo",
    "zendesk", "udemy", "qualtrics", "wayfair", "remitly",
    "mozilla", "canonical", "canonicaljobs", "canonicalcareers",
    "thoughtspot", "talkdesk", "sendbird", "supabase", "ramp",
    "rippling", "cointracker", "intercom", "whoop", "1password",
    "mattermost", "grafana", "confluentinc"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}


def load_existing_sources():
    if not os.path.exists(SOURCE_FILE):
        print("⚠️ internship_sources.json not found. Creating new file.")
        return []

    try:
        with open(SOURCE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            print("⚠️ internship_sources.json is not a JSON list. Creating backup and starting fresh.")
            shutil.copy(SOURCE_FILE, BACKUP_FILE)
            return []

        return data

    except json.JSONDecodeError as e:
        print("❌ internship_sources.json has invalid JSON.")
        print(f"Line: {e.lineno}, Column: {e.colno}")
        print("Message:", e.msg)

        with open(SOURCE_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        start = max(e.lineno - 3, 0)
        end = min(e.lineno + 3, len(lines))

        print("\nProblem area:")
        for i in range(start, end):
            print(f"{i + 1}: {lines[i].rstrip()}")

        shutil.copy(SOURCE_FILE, BACKUP_FILE)
        print(f"\n📦 Backup created: {BACKUP_FILE}")
        print("⚠️ Starting with empty list so script can continue.")

        return []

    except Exception as e:
        print("❌ Failed to load internship_sources.json:", e)
        return []


def save_sources(sources):
    sources = sorted(
        sources,
        key=lambda x: (
            x.get("ats", "").lower(),
            x.get("company", "").lower(),
            x.get("board", "").lower()
        )
    )

    with open(SOURCE_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2, ensure_ascii=False)

    print(f"✅ Saved valid JSON to {SOURCE_FILE}")


def already_exists(sources, ats, board):
    for source in sources:
        if (
            source.get("ats", "").lower() == ats.lower()
            and source.get("board", "").lower() == board.lower()
        ):
            return True
    return False


def make_company_name(board):
    manual_names = {
        "confluentinc": "Confluent",
        "redditinc": "Reddit",
        "canonicaljobs": "Canonical",
        "canonicalcareers": "Canonical",
        "1password": "1Password"
    }

    if board in manual_names:
        return manual_names[board]

    return board.replace("-", " ").replace("_", " ").title()


def check_greenhouse_board(board):
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)

        if response.status_code != 200:
            return False, 0

        data = response.json()
        jobs = data.get("jobs", [])

        return True, len(jobs)

    except Exception:
        return False, 0


def remove_duplicate_sources(sources):
    unique_sources = []
    seen = set()

    for source in sources:
        ats = str(source.get("ats", "")).lower().strip()
        board = str(source.get("board", "")).lower().strip()

        if not ats or not board:
            continue

        key = f"{ats}:{board}"

        if key in seen:
            continue

        seen.add(key)
        unique_sources.append(source)

    return unique_sources


def main():
    existing_sources = load_existing_sources()
    existing_sources = remove_duplicate_sources(existing_sources)

    added_sources = []

    print("\n🚀 Checking Greenhouse boards...\n")

    for board in boards:
        board = board.strip()

        if already_exists(existing_sources, "greenhouse", board):
            print(f"⏭️ Already exists: {board}")
            continue

        is_valid, job_count = check_greenhouse_board(board)

        if is_valid:
            print(f"✅ {board} | Jobs: {job_count}")

            new_source = {
                "company": make_company_name(board),
                "ats": "greenhouse",
                "board": board
            }

            existing_sources.append(new_source)
            added_sources.append(new_source)

        else:
            print(f"❌ {board} | Not valid")

        time.sleep(0.5)

    save_sources(existing_sources)

    print("\n🎯 New sources added:", len(added_sources))
    print("📂 Updated:", SOURCE_FILE)

    if added_sources:
        print("\n✅ Added sources:")
        for source in added_sources:
            print(source)


if __name__ == "__main__":
    main()