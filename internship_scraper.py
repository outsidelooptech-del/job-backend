import json
import time
import requests
from bs4 import BeautifulSoup

from database import get_connection
from save_internship import save_internship


# ===============================
# CONFIG
# ===============================

SOURCE_FILE = "internship_sources.json"
OUTPUT_FILE = "internships_output.json"

MAX_INTERNSHIPS = 500
REQUEST_TIMEOUT = 30
SLEEP_BETWEEN_COMPANIES = 1

HEADERS_JSON = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

HEADERS_HTML = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html"
}


# ===============================
# INTERNSHIP DETECTOR
# ===============================

def is_internship(title, description="", keywords=None):
    title_text = f" {title or ''} ".lower()
    keyword_text = f" {' '.join(keywords or [])} ".lower()

    reject_terms = [
        " senior ",
        " manager ",
        " lead ",
        " principal ",
        " director ",
        " architect ",
        " staff engineer ",
        " vice president ",
        " vp ",
        " head ",
        " 5-7 ",
        " 7-11 ",
        " 10-15 ",
        " 4-8yrs ",
        " 4-8 years ",
        " 5-7 years ",
        " 7 to 11 years "
    ]

    for term in reject_terms:
        if term in title_text:
            return False

    title_strong_terms = [
        " intern ",
        " internship ",
        " summer intern ",
        " winter intern ",
        " graduate intern ",
        " software intern ",
        " engineering intern ",
        " data intern ",
        " analyst intern ",
        " marketing intern ",
        " trainee ",
        " apprentice ",
        " co-op "
    ]

    keyword_strong_terms = [
        " intern ",
        " internship ",
        " trainee ",
        " apprentice ",
        " co-op "
    ]

    for term in title_strong_terms:
        if term in title_text:
            return True

    for term in keyword_strong_terms:
        if term in keyword_text:
            return True

    return False


# ===============================
# HELPERS
# ===============================

def strip_html(html):
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n").strip()


def load_sources():
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_list(values):
    cleaned = []

    for value in values:
        if value is None:
            continue

        value = str(value).strip()

        if value and value not in cleaned:
            cleaned.append(value)

    return cleaned


def normalize_location(value):
    if not value:
        return "Global"

    value = str(value).strip()

    if value.lower() in [
        "remote - global",
        "remote global",
        "global remote",
        "remote"
    ]:
        return "Remote"

    return value


def safe_posted_at_from_ms(timestamp_ms):
    if not timestamp_ms:
        return None

    try:
        return time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime(timestamp_ms / 1000)
        )
    except Exception:
        return None


def should_skip_source(source):
    return source.get("enabled", True) is False


def is_duplicate_link(link, seen_links):
    if not link:
        return True

    if link in seen_links:
        return True

    seen_links.add(link)

    return False


# ===============================
# GREENHOUSE HELPERS
# ===============================

def get_greenhouse_job_description(job):
    return strip_html(job.get("content", ""))


def extract_greenhouse_department(job):
    departments = job.get("departments") or []

    if departments and departments[0].get("name"):
        return departments[0].get("name")

    return "Not specified"


def extract_greenhouse_location(job):
    return normalize_location(
        job.get("location", {}).get("name")
    )


# ===============================
# LEVER HELPERS
# ===============================

def get_lever_job_description(job):
    description = job.get("descriptionPlain") or ""

    content = job.get("content") or {}

    if content.get("description"):
        description += "\n" + strip_html(content.get("description"))

    lists = content.get("lists") or []

    for item in lists:
        description += "\n" + strip_html(item.get("text", ""))
        description += "\n" + strip_html(item.get("content", ""))

    return description.strip()


def extract_lever_location(categories):
    return normalize_location(
        categories.get("location") or "Remote"
    )


# ===============================
# GREENHOUSE SCRAPER
# ===============================

def scrape_greenhouse(source, cur):
    company = source["company"]
    board = source["board"]

    url = source.get("url") or f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"

    print(f"\n🟢 Greenhouse: {company}")

    internships = []
    seen_links = set()

    try:
        response = requests.get(
            url,
            headers=HEADERS_JSON,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 404:
            print(f"⚠️ Board not found: {board}")
            return []

        if response.status_code != 200:
            print("❌ Failed:", response.status_code)
            return []

        data = response.json()
        jobs = data.get("jobs", [])

        for job in jobs:
            title = job.get("title", "") or ""
            description = get_greenhouse_job_description(job)
            department = extract_greenhouse_department(job)
            location = extract_greenhouse_location(job)

            keywords = clean_list([
                job.get("requisition_id"),
                department,
                job.get("updated_at"),
                location,
                "Greenhouse"
            ])

            if not is_internship(title, description, keywords):
                continue

            apply_link = job.get("absolute_url")

            if is_duplicate_link(apply_link, seen_links):
                continue

            internship_data = {
                "company": company,
                "title": title,
                "location": location,
                "apply_link": apply_link,
                "keywords": keywords,
                "source": "Greenhouse",
                "department": department,
                "internship_description": description,
                "company_description": f"{company} internship and early career opportunities.",
                "posted_at": job.get("updated_at")
            }

            internships.append(internship_data)

            print("✅ Saving internship:", title)

            save_internship(internship_data, cur)

        print(f"🎯 {len(internships)} internships found from {company}")

        return internships

    except Exception as e:
        print("❌ Greenhouse error:", company, e)
        return []


# ===============================
# LEVER SCRAPER
# ===============================

def scrape_lever(source, cur):
    company = source["company"]
    board = source["board"]

    url = source.get("url") or f"https://api.lever.co/v0/postings/{board}?mode=json"

    print(f"\n🔵 Lever: {company}")

    internships = []
    seen_links = set()

    try:
        response = requests.get(
            url,
            headers=HEADERS_JSON,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 404:
            print(f"⚠️ Board not found: {board}")
            return []

        if response.status_code != 200:
            print("❌ Failed:", response.status_code)
            return []

        jobs = response.json()

        for job in jobs:
            title = job.get("text", "") or ""
            description = get_lever_job_description(job)

            categories = job.get("categories", {}) or {}

            department = (
                categories.get("team")
                or categories.get("department")
                or "Not specified"
            )

            location = extract_lever_location(categories)

            keywords = clean_list([
                department,
                categories.get("commitment"),
                categories.get("location"),
                categories.get("level"),
                "Lever"
            ])

            if not is_internship(title, description, keywords):
                continue

            apply_link = job.get("hostedUrl") or job.get("applyUrl")

            if is_duplicate_link(apply_link, seen_links):
                continue

            internship_data = {
                "company": company,
                "title": title,
                "location": location,
                "apply_link": apply_link,
                "keywords": keywords,
                "source": "Lever",
                "department": department,
                "internship_description": description,
                "company_description": f"{company} internship and early career opportunities.",
                "posted_at": safe_posted_at_from_ms(job.get("createdAt"))
            }

            internships.append(internship_data)

            print("✅ Saving internship:", title)

            save_internship(internship_data, cur)

        print(f"🎯 {len(internships)} internships found from {company}")

        return internships

    except Exception as e:
        print("❌ Lever error:", company, e)
        return []


# ===============================
# ASHBY SCRAPER
# ===============================

def scrape_ashby(source, cur):
    company = source["company"]
    board = source["board"]

    url = source.get("url") or f"https://jobs.ashbyhq.com/{board}"

    print(f"\n🟣 Ashby: {company}")

    internships = []
    seen_links = set()

    try:
        response = requests.get(
            url,
            headers=HEADERS_HTML,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 404:
            print(f"⚠️ Ashby board not found: {board}")
            return []

        if response.status_code != 200:
            print("❌ Failed:", response.status_code)
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        links = soup.find_all("a", href=True)

        for link in links:
            title = link.get_text(" ", strip=True)
            href = link.get("href")

            if not title or not href:
                continue

            if not is_internship(title):
                continue

            if href.startswith("/"):
                apply_link = "https://jobs.ashbyhq.com" + href
            elif href.startswith("http"):
                apply_link = href
            else:
                continue

            if is_duplicate_link(apply_link, seen_links):
                continue

            internship_data = {
                "company": company,
                "title": title,
                "location": source.get("location") or "Global",
                "apply_link": apply_link,
                "keywords": clean_list([
                    "Ashby",
                    source.get("location"),
                    source.get("tag")
                ]),
                "source": "Ashby",
                "department": "Not specified",
                "internship_description": "",
                "company_description": f"{company} internship and early career opportunities.",
                "posted_at": None
            }

            internships.append(internship_data)

            print("✅ Saving internship:", title)

            save_internship(internship_data, cur)

        print(f"🎯 {len(internships)} internships found from {company}")

        return internships

    except Exception as e:
        print("❌ Ashby error:", company, e)
        return []


# ===============================
# MAIN SCRAPER
# ===============================

def run_internship_scraper():
    sources = load_sources()

    all_internships = []

    conn = get_connection()
    cur = conn.cursor()

    print("🚀 Starting Internship Scraper...\n")

    try:
        for source in sources:
            if len(all_internships) >= MAX_INTERNSHIPS:
                break

            if should_skip_source(source):
                print("⏭️ Skipping disabled source:", source.get("company"))
                continue

            ats = source.get("ats")
            results = []

            if ats == "greenhouse":
                results = scrape_greenhouse(source, cur)

            elif ats == "lever":
                results = scrape_lever(source, cur)

            elif ats == "ashby":
                results = scrape_ashby(source, cur)

            else:
                print("❌ Unsupported ATS:", ats, "|", source.get("company"))

            all_internships.extend(results)

            conn.commit()

            time.sleep(SLEEP_BETWEEN_COMPANIES)

        print(f"\n✅ Total internships saved: {len(all_internships)}")

    except Exception as e:
        conn.rollback()
        print("❌ Fatal Error:", e)

    finally:
        cur.close()
        conn.close()

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            all_internships,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("📂 Output saved to:", OUTPUT_FILE)

    return all_internships


# ===============================
# RUN
# ===============================

if __name__ == "__main__":
    run_internship_scraper()