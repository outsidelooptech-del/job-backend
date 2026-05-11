import requests
import json
import time

from database import get_connection
from save_job import save_job


COMPANY_NAME = "American Express"
COMPANY_DOMAIN = "americanexpress.com"
COMPANY_LOGO = "https://img.logo.dev/americanexpress.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

PAGE_URL = "https://aexp.eightfold.ai/careers?location=India"

BASE_API = (
    "https://aexp.eightfold.ai/api/apply/v2/jobs"
    "?domain=aexp.com&location=India&sort_by=relevance"
)

MAX_LIMIT = 700


def detect_work_mode(location):
    if not location:
        return "Onsite"

    text = location.lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, employment_type):
    text = f"{title or ''} {employment_type or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return employment_type or "Full Time"


def detect_experience(title, experience_level):
    text = f"{title or ''} {experience_level or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "manager" in text or "lead" in text or "director" in text:
        return "5+ yrs"

    return experience_level or "Not specified"


def fetch_american_express_jobs():

    session = requests.Session()

    conn = get_connection()
    cur = conn.cursor()

    try:
        session.get(
            PAGE_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30
        )

        csrf_token = session.cookies.get("csrf_token")

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": PAGE_URL
        }

        if csrf_token:
            headers["x-csrf-token"] = csrf_token

        start = 0
        num = 10
        page = 1

        all_jobs = []
        seen_links = set()

        print("Started fetching American Express India jobs...")

        while True:

            if len(all_jobs) >= MAX_LIMIT:
                print("Reached job limit. Stopping scraper.")
                break

            print(f"\nScraping {COMPANY_NAME} India jobs — page {page}")

            url = f"{BASE_API}&start={start}&num={num}"

            try:
                response = session.get(
                    url,
                    headers=headers,
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
                print("Invalid JSON response")
                break

            jobs = data.get("positions", [])

            if not jobs:
                print("No more jobs found.")
                break

            new_found = 0

            for job in jobs:

                if len(all_jobs) >= MAX_LIMIT:
                    break

                title = (job.get("name") or "").strip()
                location = (job.get("location") or "").strip()
                apply_link = (job.get("canonicalPositionUrl") or "").strip()

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)
                new_found += 1

                department = job.get("department")
                employment_type = job.get("employmentType")
                experience_level = job.get("experienceLevel")
                category = job.get("category")

                keywords = list(filter(None, [
                    department,
                    employment_type,
                    experience_level,
                    category
                ]))

                job_description = (
                    job.get("description")
                    or job.get("jobDescription")
                    or job.get("shortDescription")
                    or ""
                )

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title or "Not Mentioned",
                    "location": location or "Not Mentioned",
                    "apply_link": apply_link,
                    "keywords": list(set(keywords)),

                    "source": "American Express Eightfold",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location),
                    "job_type": detect_job_type(title, employment_type),
                    "experience": detect_experience(title, experience_level),
                    "education": "Not specified",
                    "department": department or category,
                    "salary": "Not disclosed",
                    "job_description": job_description,
                    "company_description": "American Express is a global payments and financial services company.",
                    "posted_at": job.get("postedDate") or job.get("createdDate")
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            if new_found == 0:
                break

            start += num
            page += 1

            time.sleep(1)

        conn.commit()

        print("Finished saving American Express jobs to database.")

        return all_jobs

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)
        return []

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":

    jobs = fetch_american_express_jobs()

    with open(
        "american_express_india_jobs.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Scraped {len(jobs)} {COMPANY_NAME} India jobs!")