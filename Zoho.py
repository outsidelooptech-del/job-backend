import os
import requests
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

COMPANY_NAME = "Zoho"
COMPANY_LOGO = "https://img.logo.dev/zoho.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://careers.zohocorp.com/recruit/v2/public/Job_Openings"

OUTPUT_FILE = "zoho_jobs.json"

MAX_JOBS = 500

PARAMS = {
    "pagename": "Careers",
    "source": "CareerSite",
    "extra_fields": '["Remote_Job"]'
}

HEADERS = {
    "accept": "application/json",
    "origin": "https://www.zoho.com",
    "referer": "https://www.zoho.com/",
    "user-agent": "Mozilla/5.0"
}


# =============================
# HELPERS
# =============================

def detect_work_mode(location, title="", remote_job=""):
    text = f"{location or ''} {title or ''} {remote_job or ''}".lower()

    if "remote" in text or remote_job is True:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, job_type_text=""):
    text = f"{title or ''} {job_type_text or ''}".lower()

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

def scrape_zoho_jobs():

    conn = psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )

    cur = conn.cursor()

    all_jobs = []

    seen_ids = set()
    seen_links = set()

    print("🚀 Fetching Zoho jobs...\n")

    try:
        response = requests.get(
            BASE_URL,
            headers=HEADERS,
            params=PARAMS,
            timeout=30
        )

        if response.status_code != 200:
            print("Request failed:", response.status_code)
            return []

        data = response.json()

        if data.get("code") != "success":
            print("API response not successful.")
            return []

        jobs = data.get("data", [])

        print("Total Jobs Found:", len(jobs))

        for job in jobs:

            if len(all_jobs) >= MAX_JOBS:
                break

            title = job.get("Posting_Title") or "Not Mentioned"
            location = job.get("Country1") or "India"
            apply_link = job.get("$url") or ""

            job_id = str(
                job.get("Job_ID")
                or job.get("id")
                or apply_link
            ).strip()

            if not apply_link:
                continue

            if job_id in seen_ids or apply_link in seen_links:
                continue

            seen_ids.add(job_id)
            seen_links.add(apply_link)

            job_type_text = job.get("Job_Type")
            remote_job = job.get("Remote_Job")

            keywords = list(set([
                str(k)
                for k in [
                    job_id,
                    job_type_text,
                    remote_job,
                    title,
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

                "source": "Zoho Careers API",
                "company_logo": COMPANY_LOGO,
                "work_mode": detect_work_mode(
                    location,
                    title,
                    remote_job
                ),
                "job_type": detect_job_type(
                    title,
                    job_type_text
                ),
                "experience": detect_experience(title),
                "education": "Not specified",
                "department": "Not specified",
                "salary": "Not disclosed",
                "job_description": "",
                "company_description": "Zoho is an Indian software company providing cloud-based business, productivity, CRM, finance, HR, and collaboration applications.",
                "posted_at": "Not specified"
            }

            all_jobs.append(job_data)

            print("Saving:", title)

            save_job(job_data, cur)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Zoho jobs to database.")

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

    jobs = scrape_zoho_jobs()

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