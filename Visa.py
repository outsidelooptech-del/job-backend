import os
import time
import json
import cloudscraper
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

COMPANY_NAME = "Visa"
COMPANY_LOGO = "https://img.logo.dev/visa.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

URL = "https://search.visa.com/CAREERS/careers/jobs?q="

OUTPUT_FILE = "visa_india_jobs.json"

MAX_JOBS = 500

scraper = cloudscraper.create_scraper()

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
    "origin": "https://www.visa.co.in",
    "referer": "https://www.visa.co.in/en_in/jobs/?cities=Bangalore&cities=Mumbai",
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

def scrape_visa_jobs():

    conn = psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )

    cur = conn.cursor()

    all_jobs = []

    seen_ids = set()
    seen_links = set()

    start = 0
    size = 10

    print("🚀 Scraping Visa India jobs...\n")

    try:
        while len(all_jobs) < MAX_JOBS:

            print(f"\nFetching jobs from {start}")

            payload = {
                "city": [
                    "Bangalore",
                    "Mumbai"
                ],
                "from": start,
                "size": size
            }

            response = scraper.post(
                URL,
                json=payload,
                headers=HEADERS,
                timeout=30
            )

            if response.status_code != 200:
                print("Request failed:", response.status_code)
                break

            data = response.json()

            total_records = data.get("recordsMatched", 0)
            jobs = data.get("jobDetails", [])

            if not jobs:
                print("No more jobs found.")
                break

            for job in jobs:

                if len(all_jobs) >= MAX_JOBS:
                    break

                title = job.get("jobTitle") or "Not Mentioned"
                location = job.get("city") or "India"
                apply_link = job.get("applyUrl") or ""

                job_id = str(
                    job.get("refNumber")
                    or job.get("postingId")
                    or apply_link
                ).strip()

                if not apply_link:
                    continue

                if job_id in seen_ids or apply_link in seen_links:
                    continue

                seen_ids.add(job_id)
                seen_links.add(apply_link)

                department = job.get("department")
                function = job.get("function")
                employment_type = job.get("typeOfEmployment")
                country = job.get("country")
                created_on = job.get("createdOn")

                keywords = list(set([
                    str(k)
                    for k in [
                        job_id,
                        job.get("postingId"),
                        department,
                        function,
                        employment_type,
                        country,
                        created_on,
                        f"Start {start}"
                    ]
                    if k
                ]))

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": keywords,

                    "source": "Visa Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title, employment_type),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": department or function or "Not specified",
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "Visa is a global payments technology company enabling digital payments, card networks, financial services, and secure money movement worldwide.",
                    "posted_at": created_on or "Not specified"
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            print("Jobs collected:", len(all_jobs))

            start += size

            if start >= total_records:
                break

            time.sleep(1)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Visa jobs to database.")

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

    jobs = scrape_visa_jobs()

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