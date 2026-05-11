import requests
import json
import time
import re
from save_job import save_job
from database import get_connection


COMPANY_NAME = "Capgemini"
COMPANY_LOGO = "https://img.logo.dev/capgemini.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

API_URL = "https://cg-job-search-microservices.azurewebsites.net/api/job-search"
OUTPUT_FILE = "capgemini_india_jobs.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Origin": "https://www.capgemini.com"
}


def clean_html(text):
    if not text:
        return ""

    return re.sub("<.*?>", "", str(text)).strip()


def detect_work_mode(location, description=""):
    text = f"{location or ''} {description or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, description=""):
    text = f"{title or ''} {description or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def normalize_experience(exp, title=""):
    text = f"{exp or ''} {title or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if exp:
        return exp

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "manager" in text or "lead" in text:
        return "5+ yrs"

    return "Not specified"


def fetch_capgemini_india_jobs():

    session = requests.Session()
    session.headers.update(HEADERS)

    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    page = 1
    size = 20
    target_jobs = 120

    print(f"Started fetching {COMPANY_NAME} India jobs...")

    try:

        while len(all_jobs) < target_jobs:

            print(f"\nScraping {COMPANY_NAME} India jobs — page={page}")

            params = {
                "page": page,
                "size": size,
                "country_code": "in-en"
            }

            try:
                r = session.get(
                    API_URL,
                    params=params,
                    timeout=30
                )

            except Exception as e:
                print("Request error:", e)
                break

            if r.status_code != 200:
                print("Request failed:", r.status_code)
                break

            try:
                data = r.json()

            except ValueError:
                print("Invalid JSON response.")
                break

            jobs = data.get("data", [])

            if not jobs:
                break

            new_found = 0

            for job in jobs:

                title = clean_html(job.get("title", ""))
                location = clean_html(job.get("location", ""))
                raw_experience = clean_html(job.get("experience_level", ""))
                apply_link = (job.get("apply_job_url") or "").strip()

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)
                new_found += 1

                job_description = clean_html(
                    job.get("description")
                    or job.get("job_description")
                    or job.get("short_description")
                    or ""
                )

                department = clean_html(
                    job.get("business_unit")
                    or job.get("category")
                    or job.get("department")
                    or ""
                ) or None

                posted_at = (
                    job.get("posted_date")
                    or job.get("created_at")
                    or job.get("updated_at")
                )

                experience = normalize_experience(raw_experience, title)

                keywords = list(set([
                    raw_experience,
                    department,
                    posted_at
                ]))

                keywords = [k for k in keywords if k]

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title or "Not Mentioned",
                    "location": location or "India",
                    "apply_link": apply_link,
                    "keywords": keywords,

                    "source": "Capgemini Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, job_description),
                    "job_type": detect_job_type(title, job_description),
                    "experience": experience,
                    "education": "Not specified",
                    "department": department,
                    "salary": "Not disclosed",
                    "job_description": job_description,
                    "company_description": "Capgemini is a global technology consulting and digital transformation company.",
                    "posted_at": posted_at
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

                if len(all_jobs) >= target_jobs:
                    break

            if new_found == 0:
                break

            page += 1
            time.sleep(0.5)

        conn.commit()

        print(f"Finished saving {COMPANY_NAME} jobs to database.")

    except Exception as e:

        conn.rollback()
        print("Fatal error:", e)

    finally:

        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs = fetch_capgemini_india_jobs()

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

    print(f"\n✅ Scraped {len(jobs)} {COMPANY_NAME} India jobs!")
    print("Saved to", OUTPUT_FILE)