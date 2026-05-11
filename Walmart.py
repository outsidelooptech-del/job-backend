import os
import requests
import time
import json
import psycopg2

from dotenv import load_dotenv

from save_job import save_job


# =============================
# LOAD ENV
# =============================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


# =============================
# CONFIG
# =============================

COMPANY_NAME = "Walmart"
COMPANY_LOGO = "https://img.logo.dev/walmart.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://walmart.wd5.myworkdayjobs.com/wday/cxs/walmart/WalmartExternal/jobs"
APPLY_BASE_URL = "https://walmart.wd5.myworkdayjobs.com/en-US/WalmartExternal"

OUTPUT_FILE = "walmart_india_jobs.json"

COUNTRY_ID_INDIA = "c4f78be1a8f14da0ab49ce1162348a5e"

LIMIT = 20
MAX_JOBS = 500

HEADERS = {
    "accept": "application/json",
    "content-type": "application/json",
    "origin": "https://walmart.wd5.myworkdayjobs.com",
    "referer": "https://walmart.wd5.myworkdayjobs.com/en-US/WalmartExternal",
    "user-agent": "Mozilla/5.0"
}


# =============================
# HELPERS
# =============================

def detect_work_mode(location, title=""):
    text = f"{location or ''} {title or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title):
    text = (title or "").lower()

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def detect_experience(title):
    text = (title or "").lower()

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


# =============================
# SCRAPER
# =============================

def scrape_walmart_jobs():

    conn = psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )

    cur = conn.cursor()

    offset = 0

    all_jobs = []

    seen_links = set()

    print("🚀 Starting Walmart India job scraping...\n")

    try:
        while len(all_jobs) < MAX_JOBS:

            payload = {
                "appliedFacets": {
                    "locationCountry": [
                        COUNTRY_ID_INDIA
                    ]
                },
                "limit": LIMIT,
                "offset": offset,
                "searchText": ""
            }

            response = requests.post(
                BASE_URL,
                headers=HEADERS,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                print("Request failed:", response.status_code)
                break

            data = response.json()

            total_jobs = data.get("total", 0)
            job_list = data.get("jobPostings", [])

            print(
                f"Fetching offset {offset} | Jobs found: {len(job_list)}"
            )

            if not job_list:
                print("No more jobs found.")
                break

            for job in job_list:

                if len(all_jobs) >= MAX_JOBS:
                    break

                title = job.get("title") or "Not Mentioned"
                location = job.get("locationsText") or "India"
                posted_on = job.get("postedOn")

                external_path = job.get("externalPath", "")

                apply_link = (
                    APPLY_BASE_URL + external_path
                    if external_path
                    else ""
                )

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)

                keywords = list(set([
                    str(k)
                    for k in [
                        posted_on,
                        location,
                        f"Offset {offset}"
                    ]
                    if k
                ]))

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": keywords,

                    "source": "Walmart Workday Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": "Not specified",
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "Walmart is a global retail and technology company operating supermarkets, e-commerce platforms, supply chain, finance, and digital commerce businesses.",
                    "posted_at": posted_on or "Not specified"
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            print("Jobs collected:", len(all_jobs))

            offset += LIMIT

            if offset >= total_jobs:
                break

            time.sleep(1)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Walmart jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


# =============================
# MAIN
# =============================

if __name__ == "__main__":

    jobs = scrape_walmart_jobs()

    print("\nTotal Jobs Scraped:", len(jobs))

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

    print("✅ Saved:", OUTPUT_FILE)