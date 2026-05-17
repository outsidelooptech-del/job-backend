import json
import time
import requests
from bs4 import BeautifulSoup

from database import get_connection
from save_internship import save_internship


SOURCE_FILE = "internship_sources.json"
OUTPUT_FILE = "internships_output.json"

MAX_INTERNSHIPS = 2000
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


def is_internship(title, description="", keywords=None):
    text = f" {title or ''} {description or ''} {' '.join(keywords or [])} ".lower()

    reject_terms = [
        "senior", "manager", "lead", "principal", "director",
        "architect", "staff engineer", "vice president", "vp",
        "head", "sde ii", "sde 2", "experienced"
    ]

    for term in reject_terms:
        if term in text:
            return False

    include_terms = [
        "intern", "internship", "summer intern", "winter intern",
        "graduate intern", "software intern", "engineering intern",
        "data intern", "analyst intern", "marketing intern",
        "trainee", "apprentice", "co-op", "student worker",
        "campus", "new grad", "early career", "graduate program"
    ]

    return any(term in text for term in include_terms)


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
        "remote - global", "remote global", "global remote", "remote"
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


def is_india_job(location):
    if not location:
        return False

    location = location.lower()

    india_keywords = [
        "india", "bangalore", "bengaluru", "hyderabad", "pune",
        "mumbai", "gurgaon", "gurugram", "chennai", "noida",
        "remote india", "delhi", "kolkata", "ahmedabad"
    ]

    return any(k in location for k in india_keywords)


def make_job_key(company, title, location):
    return f"{company}_{title}_{location}".lower().strip()


def get_greenhouse_job_description(job):
    return strip_html(job.get("content", ""))


def extract_greenhouse_department(job):
    departments = job.get("departments") or []

    if departments and departments[0].get("name"):
        return departments[0].get("name")

    return "Not specified"


def extract_greenhouse_location(job):
    return normalize_location(job.get("location", {}).get("name"))


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
    return normalize_location(categories.get("location") or "Remote")


def scrape_greenhouse(source, cur, global_seen_jobs):
    company = source["company"]
    board = source["board"]

    url = source.get("url") or f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"

    print(f"\n🟢 Greenhouse: {company}")

    internships = []
    seen_links = set()

    try:
        response = requests.get(url, headers=HEADERS_JSON, timeout=REQUEST_TIMEOUT)

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

            job_key = make_job_key(company, title, location)
            if job_key in global_seen_jobs:
                continue
            global_seen_jobs.add(job_key)

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
                "posted_at": job.get("updated_at"),
                "priority": 2 if is_india_job(location) else 1
            }

            internships.append(internship_data)
            print("✅ Saving internship:", title)
            save_internship(internship_data, cur)

        print(f"🎯 {len(internships)} internships found from {company}")
        return internships

    except Exception as e:
        print("❌ Greenhouse error:", company, e)
        return []


def scrape_lever(source, cur, global_seen_jobs):
    company = source["company"]
    board = source["board"]

    url = source.get("url") or f"https://api.lever.co/v0/postings/{board}?mode=json"

    print(f"\n🔵 Lever: {company}")

    internships = []
    seen_links = set()

    try:
        response = requests.get(url, headers=HEADERS_JSON, timeout=REQUEST_TIMEOUT)

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

            job_key = make_job_key(company, title, location)
            if job_key in global_seen_jobs:
                continue
            global_seen_jobs.add(job_key)

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
                "posted_at": safe_posted_at_from_ms(job.get("createdAt")),
                "priority": 2 if is_india_job(location) else 1
            }

            internships.append(internship_data)
            print("✅ Saving internship:", title)
            save_internship(internship_data, cur)

        print(f"🎯 {len(internships)} internships found from {company}")
        return internships

    except Exception as e:
        print("❌ Lever error:", company, e)
        return []


def scrape_ashby(source, cur, global_seen_jobs):
    company = source["company"]
    board = source["board"]

    url = source.get("url") or f"https://jobs.ashbyhq.com/{board}"

    print(f"\n🟣 Ashby: {company}")

    internships = []
    seen_links = set()

    try:
        response = requests.get(url, headers=HEADERS_HTML, timeout=REQUEST_TIMEOUT)

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

            location = source.get("location") or "Global"

            job_key = make_job_key(company, title, location)
            if job_key in global_seen_jobs:
                continue
            global_seen_jobs.add(job_key)

            internship_data = {
                "company": company,
                "title": title,
                "location": location,
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
                "posted_at": None,
                "priority": 2 if is_india_job(location) else 1
            }

            internships.append(internship_data)
            print("✅ Saving internship:", title)
            save_internship(internship_data, cur)

        print(f"🎯 {len(internships)} internships found from {company}")
        return internships

    except Exception as e:
        print("❌ Ashby error:", company, e)
        return []


def scrape_smartrecruiters(source, cur, global_seen_jobs):
    company = source["company"]
    board = source["board"]

    url = source.get("url") or f"https://api.smartrecruiters.com/v1/companies/{board}/postings"

    print(f"\n🟠 SmartRecruiters: {company}")

    internships = []
    seen_links = set()

    try:
        response = requests.get(url, headers=HEADERS_JSON, timeout=REQUEST_TIMEOUT)

        if response.status_code == 404:
            print(f"⚠️ SmartRecruiters board not found: {board}")
            return []

        if response.status_code != 200:
            print("❌ Failed:", response.status_code)
            return []

        data = response.json()
        jobs = data.get("content", [])

        for job in jobs:
            title = job.get("name", "") or ""

            location_data = job.get("location") or {}
            location = normalize_location(
                location_data.get("city")
                or location_data.get("region")
                or location_data.get("country")
                or "Global"
            )

            department_data = job.get("department")
            department = (
                department_data.get("label")
                if isinstance(department_data, dict)
                else "Not specified"
            ) or "Not specified"

            apply_link = job.get("ref") or job.get("applyUrl")

            keywords = clean_list([
                department,
                location,
                "SmartRecruiters"
            ])

            if not is_internship(title, "", keywords):
                continue

            if is_duplicate_link(apply_link, seen_links):
                continue

            job_key = make_job_key(company, title, location)
            if job_key in global_seen_jobs:
                continue
            global_seen_jobs.add(job_key)

            internship_data = {
                "company": company,
                "title": title,
                "location": location,
                "apply_link": apply_link,
                "keywords": keywords,
                "source": "SmartRecruiters",
                "department": department,
                "internship_description": "",
                "company_description": f"{company} internship and early career opportunities.",
                "posted_at": job.get("releasedDate"),
                "priority": 2 if is_india_job(location) else 1
            }

            internships.append(internship_data)
            print("✅ Saving internship:", title)
            save_internship(internship_data, cur)

        print(f"🎯 {len(internships)} internships found from {company}")
        return internships

    except Exception as e:
        print("❌ SmartRecruiters error:", company, e)
        return []


def scrape_workable(source, cur, global_seen_jobs):
    company = source["company"]
    board = source["board"]

    url = source.get("url") or f"https://apply.workable.com/api/v3/accounts/{board}/jobs"

    print(f"\n🟡 Workable: {company}")

    internships = []
    seen_links = set()

    try:
        response = requests.get(url, headers=HEADERS_JSON, timeout=REQUEST_TIMEOUT)

        if response.status_code == 404:
            print(f"⚠️ Workable board not found: {board}")
            return []

        if response.status_code != 200:
            print("❌ Failed:", response.status_code)
            return []

        data = response.json()
        jobs = data.get("results", [])

        for job in jobs:
            title = job.get("title", "") or ""

            location = normalize_location(
                job.get("location", {}).get("location_str")
                or "Remote"
            )

            apply_link = f"https://apply.workable.com/{board}/j/{job.get('shortcode')}"

            keywords = clean_list([
                location,
                "Workable"
            ])

            if not is_internship(title, "", keywords):
                continue

            if is_duplicate_link(apply_link, seen_links):
                continue

            job_key = make_job_key(company, title, location)
            if job_key in global_seen_jobs:
                continue
            global_seen_jobs.add(job_key)

            internship_data = {
                "company": company,
                "title": title,
                "location": location,
                "apply_link": apply_link,
                "keywords": keywords,
                "source": "Workable",
                "department": "Not specified",
                "internship_description": "",
                "company_description": f"{company} internship and early career opportunities.",
                "posted_at": job.get("published"),
                "priority": 2 if is_india_job(location) else 1
            }

            internships.append(internship_data)
            print("✅ Saving internship:", title)
            save_internship(internship_data, cur)

        print(f"🎯 {len(internships)} internships found from {company}")
        return internships

    except Exception as e:
        print("❌ Workable error:", company, e)
        return []


def scrape_workday(source, cur, global_seen_jobs):
    company = source["company"]
    base_url = source.get("url")

    if not base_url:
        print(f"❌ Workday URL missing: {company}")
        return []

    print(f"\n🟤 Workday: {company}")

    internships = []
    seen_links = set()

    api_url = base_url.rstrip("/") + "/jobs"

    payload = {
        "appliedFacets": {},
        "limit": 100,
        "offset": 0,
        "searchText": ""
    }

    try:
        response = requests.post(
            api_url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            print("❌ Failed:", response.status_code)
            return []

        try:
            data = response.json()
        except Exception:
            print("❌ Workday non-JSON response")
            return []

        jobs = data.get("jobPostings", [])

        for job in jobs:
            title = job.get("title", "") or ""
            location = normalize_location(job.get("locationsText") or "Global")

            external_path = job.get("externalPath")
            apply_link = base_url.rstrip("/") + external_path if external_path else base_url

            keywords = clean_list([
                location,
                "Workday"
            ])

            if not is_internship(title, "", keywords):
                continue

            if is_duplicate_link(apply_link, seen_links):
                continue

            job_key = make_job_key(company, title, location)
            if job_key in global_seen_jobs:
                continue
            global_seen_jobs.add(job_key)

            internship_data = {
                "company": company,
                "title": title,
                "location": location,
                "apply_link": apply_link,
                "keywords": keywords,
                "source": "Workday",
                "department": "Not specified",
                "internship_description": "",
                "company_description": f"{company} internship and early career opportunities.",
                "posted_at": job.get("postedOn"),
                "priority": 2 if is_india_job(location) else 1
            }

            internships.append(internship_data)
            print("✅ Saving internship:", title)
            save_internship(internship_data, cur)

        print(f"🎯 {len(internships)} internships found from {company}")
        return internships

    except Exception as e:
        print("❌ Workday error:", company, e)
        return []


def run_internship_scraper():
    sources = load_sources()
    all_internships = []
    global_seen_jobs = set()

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

            ats = str(source.get("ats", "")).lower().strip()
            results = []

            if ats == "greenhouse":
                results = scrape_greenhouse(source, cur, global_seen_jobs)

            elif ats == "lever":
                results = scrape_lever(source, cur, global_seen_jobs)

            elif ats == "ashby":
                results = scrape_ashby(source, cur, global_seen_jobs)

            elif ats == "smartrecruiters":
                results = scrape_smartrecruiters(source, cur, global_seen_jobs)

            elif ats == "workable":
                results = scrape_workable(source, cur, global_seen_jobs)

            elif ats == "workday":
                results = scrape_workday(source, cur, global_seen_jobs)

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

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_internships, f, indent=4, ensure_ascii=False)

    print("📂 Output saved to:", OUTPUT_FILE)

    return all_internships


if __name__ == "__main__":
    run_internship_scraper()