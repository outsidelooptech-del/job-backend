import requests
import json

from bs4 import BeautifulSoup

from save_job import save_job
from database import get_connection


# =============================
# CONFIG
# =============================

COMPANY_NAME = "Razorpay"
COMPANY_LOGO = "https://img.logo.dev/razorpay.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

URL = "https://boards-api.greenhouse.io/v1/boards/razorpaysoftwareprivatelimited/jobs?content=true"
OUTPUT_FILE = "razorpay_jobs.json"

MAX_JOBS = 500

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
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

def scrape_razorpay_jobs():

    conn = get_connection()
    cur = conn.cursor()

    all_jobs = []
    seen_ids = set()
    seen_links = set()

    print("🚀 Fetching Razorpay jobs...\n")

    try:
        response = requests.get(
            URL,
            headers=HEADERS,
            timeout=30
        )

        if response.status_code != 200:
            print("Request failed:", response.status_code)
            return []

        data = response.json()

        for job in data.get("jobs", []):

            if len(all_jobs) >= MAX_JOBS:
                break

            title = job.get("title") or "Not Mentioned"
            location = job.get("location", {}).get("name") or "India"
            apply_link = job.get("absolute_url") or ""
            job_id = str(job.get("id") or job.get("requisition_id") or apply_link)

            if not apply_link:
                continue

            if job_id in seen_ids or apply_link in seen_links:
                continue

            seen_ids.add(job_id)
            seen_links.add(apply_link)

            description_html = job.get("content", "")
            soup = BeautifulSoup(description_html, "html.parser")
            description_text = soup.get_text(separator="\n").strip()

            departments = job.get("departments") or []
            department = departments[0].get("name") if departments else None

            posted_at = job.get("first_published")
            updated_at = job.get("updated_at")
            requisition_id = job.get("requisition_id")

            keywords = list(set([
                str(k)
                for k in [
                    requisition_id,
                    job.get("id"),
                    department,
                    posted_at,
                    updated_at,
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

                "source": "Razorpay Greenhouse API",
                "company_logo": COMPANY_LOGO,
                "work_mode": detect_work_mode(location, title),
                "job_type": detect_job_type(title),
                "experience": detect_experience(title),
                "education": "Not specified",
                "department": department or "Not specified",
                "salary": "Not disclosed",
                "job_description": description_text,
                "company_description": "Razorpay is an Indian fintech company providing payment gateway, banking, lending, payroll, and financial technology solutions for businesses.",
                "posted_at": posted_at
            }

            all_jobs.append(job_data)

            print("Saving:", title)

            save_job(job_data, cur)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Razorpay jobs to database.")

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

    jobs_data = scrape_razorpay_jobs()

    print("Total Jobs Collected:", len(jobs_data))

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