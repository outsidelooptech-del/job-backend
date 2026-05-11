import requests
import json
import time

from save_job import save_job
from database import get_connection


# =============================
# CONFIG
# =============================

COMPANY_NAME = "PepsiCo"
COMPANY_LOGO = "https://img.logo.dev/pepsico.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://www.pepsicojobs.com/api/jobs"
OUTPUT_FILE = "pepsico_india_jobs.json"

MAX_JOBS = 500

SESSION = requests.Session()

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "referer": "https://www.pepsicojobs.com/main/jobs?country=India&page=1",
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


def detect_job_type(title, employment_type=""):
    text = f"{title or ''} {employment_type or ''}".lower()

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

def scrape_pepsico_jobs():

    conn = get_connection()
    cur = conn.cursor()

    jobs_collected = []
    seen_ids = set()
    seen_links = set()

    page = 1

    print("🚀 Fetching PepsiCo India jobs...\n")

    try:
        while len(jobs_collected) < MAX_JOBS:

            params = {
                "country": "India",
                "page": page,
                "sortBy": "relevance",
                "descending": "false",
                "internal": "false"
            }

            response = SESSION.get(
                BASE_URL,
                headers=HEADERS,
                params=params,
                timeout=30
            )

            if response.status_code != 200:
                print("Request failed:", response.status_code)
                break

            data = response.json()
            jobs_list = data.get("jobs", [])

            if not jobs_list:
                print("No more jobs found.")
                break

            for item in jobs_list:

                if len(jobs_collected) >= MAX_JOBS:
                    break

                job = item.get("data", {})

                title = job.get("title") or "Not Mentioned"
                location = job.get("full_location") or "India"
                apply_link = job.get("apply_url") or ""
                job_id = job.get("req_id") or apply_link

                if not apply_link:
                    continue

                if job_id in seen_ids or apply_link in seen_links:
                    continue

                seen_ids.add(job_id)
                seen_links.add(apply_link)

                categories = job.get("categories") or []
                category_text = ", ".join(
                    [
                        c.get("name", "")
                        for c in categories
                        if c.get("name")
                    ]
                )

                employment_type = job.get("employment_type")
                posted_date = job.get("posted_date")
                city = job.get("city")
                state = job.get("state")

                keywords = list(set([
                    str(k)
                    for k in [
                        job_id,
                        employment_type,
                        category_text,
                        posted_date,
                        city,
                        state
                    ]
                    if k
                ]))

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": keywords,

                    "source": "PepsiCo Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title, employment_type),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": category_text or "Not specified",
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "PepsiCo is a global food and beverage company with brands across snacks, beverages, nutrition, and consumer products.",
                    "posted_at": posted_date
                }

                jobs_collected.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            print(f"Collected {len(jobs_collected)} jobs (page {page})")

            page += 1
            time.sleep(0.5)

        conn.commit()

        print(f"\n✅ Saved {len(jobs_collected)} PepsiCo jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return jobs_collected


# =============================
# MAIN
# =============================

if __name__ == "__main__":

    jobs_data = scrape_pepsico_jobs()

    print(f"\n✅ Total jobs collected: {len(jobs_data)}")

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            jobs_data,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("📂 Saved to", OUTPUT_FILE)