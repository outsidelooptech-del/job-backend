import requests
import json
import time

from save_job import save_job
from database import get_connection


# ===============================
# CONFIG
# ===============================

COMPANY_NAME = "Bain & Company"

COMPANY_LOGO = "https://img.logo.dev/bain.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://www.bain.com"

API_URL = "https://www.bain.com/en/api/jobsearch/keyword/get"

OUTPUT_FILE = "bain_india_jobs.json"

MAX_JOBS = 500


# ===============================
# SESSION
# ===============================

session = requests.Session()

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.bain.com/careers/find-a-role/",
    "Origin": "https://www.bain.com"
}

session.headers.update(headers)

# Warm session
try:
    session.get(
        "https://www.bain.com/careers/find-a-role/",
        timeout=30
    )
except Exception:
    pass


# ===============================
# HELPERS
# ===============================

INDIAN_CITIES = [
    "bengaluru",
    "bangalore",
    "mumbai",
    "chennai",
    "hyderabad",
    "kolkata",
    "pune",
    "delhi",
    "gurgaon",
    "noida",
    "india"
]


def normalize_location(location_list):

    if not location_list:
        return "India"

    joined = ", ".join(location_list).lower()

    for city in INDIAN_CITIES:

        if city in joined:

            if city in ["bangalore", "bengaluru"]:
                return "Bengaluru"

            if city == "gurgaon":
                return "Gurugram"

            return city.capitalize()

    return "India"


def detect_work_mode(location, title=""):

    text = f"{location or ''} {title or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, keywords=None):

    text = (title or "").lower()
    kw = " ".join(keywords or []).lower()

    if "intern" in text or "intern" in kw:
        return "Internship"

    if "contract" in text or "contract" in kw:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def detect_experience(title, keywords=None):

    text = ((title or "") + " " + " ".join(keywords or [])).lower()

    if "intern" in text:
        return "Internship"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if (
        "manager" in text
        or "lead" in text
        or "principal" in text
        or "architect" in text
        or "director" in text
        or "staff" in text
    ):
        return "5+ yrs"

    return "Not specified"


# ===============================
# SCRAPER
# ===============================

def fetch_bain_india_jobs():

    all_jobs = []
    seen_links = set()

    page = 0

    print(f"🚀 Scraping {COMPANY_NAME} India jobs...\n")

    conn = get_connection()
    cur = conn.cursor()

    try:

        while len(all_jobs) < MAX_JOBS:

            print(f"\nScraping page {page}")

            params = {
                "start": page,
                "results": 10,
                "filters": "offices(274,276,275)|",
                "searchValue": ""
            }

            try:
                response = session.get(
                    API_URL,
                    params=params,
                    timeout=30
                )

            except Exception as e:
                print("Request error:", e)
                break

            if response.status_code != 200:
                print("Request failed:", response.status_code)
                break

            try:
                data = response.json()

            except ValueError:
                print("Invalid JSON response.")
                break

            jobs = data.get("results", [])

            if not jobs:
                break

            for job in jobs:

                if len(all_jobs) >= MAX_JOBS:
                    break

                try:
                    title = job.get(
                        "JobTitle",
                        ""
                    ).strip() or "Not Mentioned"

                    locations_raw = job.get("Location", [])

                    location = normalize_location(
                        locations_raw
                    )

                    link_part = job.get(
                        "Link",
                        ""
                    ).strip()

                    if not link_part:
                        continue

                    apply_link = BASE_URL + link_part

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    keywords = list(set([
                        str(k)
                        for k in [
                            job.get("Category"),
                            job.get("JobType"),
                            job.get("PostingDate"),
                            job.get("ReqId")
                        ]
                        if k
                    ]))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title,
                        "location": location or "India",
                        "apply_link": apply_link,
                        "keywords": keywords,

                        "source": "Bain Careers",
                        "company_logo": COMPANY_LOGO,

                        "work_mode": detect_work_mode(
                            location,
                            title
                        ),

                        "job_type": detect_job_type(
                            title,
                            keywords
                        ),

                        "experience": detect_experience(
                            title,
                            keywords
                        ),

                        "education": "Not specified",

                        "department":
                            job.get("Category")
                            or "Not specified",

                        "salary": "Not disclosed",

                        "job_description": "",

                        "company_description":
                            "Bain & Company is a global management consulting firm providing strategy, operations, digital transformation, analytics, and technology consulting services.",

                        "posted_at": None
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping job due to error:", e)
                    continue

            page += 1
            time.sleep(1)

        conn.commit()

        print(
            f"\n✅ Saved {len(all_jobs)} "
            f"{COMPANY_NAME} jobs to database."
        )

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


# ===============================
# RUN
# ===============================

if __name__ == "__main__":

    jobs = fetch_bain_india_jobs()

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            jobs,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"\n✅ Scraped {len(jobs)} "
        f"{COMPANY_NAME} India jobs!"
    )

    print("Saved to", OUTPUT_FILE)
