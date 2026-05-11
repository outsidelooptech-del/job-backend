import requests
import json
import time

from save_job import save_job
from database import get_connection


# =============================
# CONFIG
# =============================

COMPANY_NAME = "Qualcomm"
COMPANY_LOGO = "https://img.logo.dev/qualcomm.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://careers.qualcomm.com/api/apply/v2/jobs"
OUTPUT_FILE = "qualcomm_india_jobs.json"

MAX_JOBS = 500

PARAMS = {
    "domain": "qualcomm.com",
    "location": "India",
    "pid": "446716971050",
    "sort_by": "relevance",
    "triggerGoButton": "false",
    "num": 10
}

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "user-agent": "Mozilla/5.0"
}


# =============================
# HELPERS
# =============================

def detect_work_mode(location, title="", work_location_option=""):
    text = f"{location or ''} {title or ''} {work_location_option or ''}".lower()

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
        or "architect"
        in text
        or "director" in text
        or "staff" in text
    ):
        return "5+ yrs"

    return "Not specified"


# =============================
# SCRAPER
# =============================

def scrape_qualcomm_jobs():

    conn = get_connection()
    cur = conn.cursor()

    start = 0

    jobs_collected = []
    seen_ids = set()
    seen_links = set()

    print("🚀 Fetching Qualcomm India jobs...\n")

    try:
        while len(jobs_collected) < MAX_JOBS:

            params = PARAMS.copy()
            params["start"] = start

            response = requests.get(
                BASE_URL,
                params=params,
                headers=HEADERS,
                timeout=30
            )

            if response.status_code != 200:
                print("Request failed:", response.status_code)
                break

            data = response.json()
            positions = data.get("positions", [])

            if not positions:
                print("No more jobs found.")
                break

            for job in positions:

                if len(jobs_collected) >= MAX_JOBS:
                    break

                title = job.get("name") or "Not Mentioned"
                location = job.get("location") or "India"
                apply_link = job.get("canonicalPositionUrl") or ""
                job_id = job.get("display_job_id") or apply_link
                department = job.get("department")
                work_location_option = job.get("work_location_option")

                if not apply_link:
                    continue

                if job_id in seen_ids or apply_link in seen_links:
                    continue

                seen_ids.add(job_id)
                seen_links.add(apply_link)

                keywords = list(set([
                    str(k)
                    for k in [
                        job_id,
                        department,
                        work_location_option,
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

                    "source": "Qualcomm Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(
                        location,
                        title,
                        work_location_option
                    ),
                    "job_type": detect_job_type(title),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": department or "Not specified",
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "Qualcomm is a global semiconductor and telecommunications technology company known for wireless technology, chipsets, processors, and mobile communication solutions.",
                    "posted_at": "Not specified"
                }

                jobs_collected.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            print(f"Collected {len(jobs_collected)} jobs")

            start += 10
            time.sleep(0.5)

        conn.commit()

        print(f"\n✅ Saved {len(jobs_collected)} Qualcomm jobs to database.")

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

    jobs_data = scrape_qualcomm_jobs()

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