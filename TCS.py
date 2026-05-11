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

COMPANY_NAME = "TCS"
COMPANY_LOGO = "https://img.logo.dev/tcs.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://ibegin.tcsapps.com/candidate/api/v1/jobs/searchJ"
APPLY_BASE = "https://ibegin.tcsapps.com/candidate/jobs/"

OUTPUT_FILE = "tcs_jobs_1000.json"

MAX_JOBS = 1000

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json;charset=UTF-8",
    "origin": "https://ibegin.tcsapps.com",
    "referer": "https://ibegin.tcsapps.com/candidate/jobs/search",
    "user-agent": "Mozilla/5.0"
}


# =============================
# HELPERS
# =============================

def get_timestamp():
    return str(int(time.time() * 1000))


def format_experience(exp):
    if not exp:
        return "Not specified"

    if "-" in exp:
        parts = exp.split("-")
        return f"{parts[0].strip()} - {parts[1].strip()} years"

    return exp + " years"


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


def detect_experience(title, exp=""):
    text = f"{title or ''} {exp or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if exp and exp != "Not specified":
        return exp

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

def scrape_tcs_jobs():

    conn = psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )
    cur = conn.cursor()

    all_jobs = []
    seen_ids = set()
    seen_links = set()

    page = 1

    print("🚀 Scraping TCS India jobs...\n")

    try:
        while len(all_jobs) < MAX_JOBS:

            print(f"Fetching Page {page}...")

            payload = {
                "jobCity": None,
                "jobSkill": None,
                "pageNumber": str(page),
                "userText": "",
                "jobTitleOrder": None,
                "jobCityOrder": None,
                "jobExperienceOrder": None,
                "jobFunctionOrder": None,
                "applyByOrder": None,
                "regular": True,
                "walkin": True
            }

            params = {
                "at": get_timestamp()
            }

            response = requests.post(
                BASE_URL,
                headers=HEADERS,
                params=params,
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                print("Request failed:", response.status_code)
                break

            data = response.json()
            jobs = data.get("data", {}).get("jobs", [])

            if not jobs:
                print("No more jobs found.")
                break

            for job in jobs:

                if len(all_jobs) >= MAX_JOBS:
                    break

                job_id = str(job.get("id", "")).strip()

                if not job_id:
                    continue

                apply_link = APPLY_BASE + job_id

                if job_id in seen_ids or apply_link in seen_links:
                    continue

                seen_ids.add(job_id)
                seen_links.add(apply_link)

                title = job.get("jobTitle", "") or "Not Mentioned"
                location = job.get("location", "") or "India"
                function_name = job.get("functionName", "")
                skills = job.get("skills", "")
                apply_by_date = job.get("applyByDate", "")
                raw_experience = job.get("experience", "")
                formatted_experience = format_experience(raw_experience)

                keywords = list(set([
                    str(k)
                    for k in [
                        job_id,
                        function_name,
                        formatted_experience,
                        skills,
                        apply_by_date,
                        f"Page {page}"
                    ]
                    if k
                ]))

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": keywords,

                    "source": "TCS iBegin Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title),
                    "experience": detect_experience(title, formatted_experience),
                    "education": "Not specified",
                    "department": function_name or "Not specified",
                    "salary": "Not disclosed",
                    "job_description": skills or "",
                    "company_description": "TCS is a global IT services, consulting, and business solutions company providing technology, digital transformation, cloud, analytics, and enterprise solutions.",
                    "posted_at": apply_by_date or "Not specified"
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            print("Collected jobs:", len(all_jobs))

            page += 1
            time.sleep(0.3)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} TCS jobs to database.")

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

    jobs = scrape_tcs_jobs()

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