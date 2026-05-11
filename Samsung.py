import requests
import json
import time

from save_job import save_job
from database import get_connection


# =============================
# CONFIG
# =============================

COMPANY_NAME = "Samsung"
COMPANY_LOGO = "https://img.logo.dev/samsung.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

API_URL = "https://sec.wd3.myworkdayjobs.com/wday/cxs/sec/Samsung_Careers/jobs"
BASE_URL = "https://sec.wd3.myworkdayjobs.com/Samsung_Careers"

OUTPUT_FILE = "samsung_india_jobs.json"

LIMIT = 20
MAX_JOBS = 500

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://sec.wd3.myworkdayjobs.com",
    "Referer": "https://sec.wd3.myworkdayjobs.com/Samsung_Careers",
    "User-Agent": "Mozilla/5.0"
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

def scrape_samsung_jobs():

    conn = get_connection()
    cur = conn.cursor()

    offset = 0

    all_jobs = []

    seen_ids = set()
    seen_links = set()

    print("🚀 Fetching Samsung India jobs...\n")

    try:

        payload = {
            "appliedFacets": {},
            "limit": LIMIT,
            "offset": offset,
            "searchText": "India"
        }

        # Initial request
        response = requests.post(
            API_URL,
            json=payload,
            headers=HEADERS,
            timeout=30
        )

        if response.status_code != 200:
            print("Initial request failed:", response.status_code)
            return []

        data = response.json()

        total_jobs = data.get("total", 0)

        print("Total returned:", total_jobs)

        while offset < total_jobs and len(all_jobs) < MAX_JOBS:

            payload["offset"] = offset

            response = requests.post(
                API_URL,
                json=payload,
                headers=HEADERS,
                timeout=30
            )

            if response.status_code != 200:
                print("Request failed:", response.status_code)
                break

            data = response.json()

            job_postings = data.get("jobPostings", [])

            if not job_postings:
                print("No more jobs found.")
                break

            for job in job_postings:

                if len(all_jobs) >= MAX_JOBS:
                    break

                location = job.get("locationsText", "")

                if not location or "India" not in location:
                    continue

                title = job.get("title") or "Not Mentioned"

                external_path = job.get("externalPath", "")
                apply_link = BASE_URL + external_path if external_path else ""

                job_id = (
                    job.get("bulletFields", [""])[0]
                    if job.get("bulletFields")
                    else apply_link
                )

                if not apply_link:
                    continue

                if job_id in seen_ids or apply_link in seen_links:
                    continue

                seen_ids.add(job_id)
                seen_links.add(apply_link)

                bullet_fields = job.get("bulletFields", [])

                department = (
                    bullet_fields[0]
                    if len(bullet_fields) > 0
                    else None
                )

                posted_on = job.get("postedOn")

                keywords = list(set([
                    str(k)
                    for k in [
                        department,
                        posted_on,
                        location
                    ]
                    if k
                ]))

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": keywords,

                    "source": "Samsung Workday Careers",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": department or "Not specified",
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "Samsung is a global technology company specializing in consumer electronics, semiconductors, mobile devices, software, and digital innovation solutions.",
                    "posted_at": posted_on
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            print(f"Collected {len(all_jobs)} jobs")

            offset += LIMIT

            time.sleep(1)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Samsung jobs to database.")

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

    jobs_data = scrape_samsung_jobs()

    print("Final India Jobs:", len(jobs_data))

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