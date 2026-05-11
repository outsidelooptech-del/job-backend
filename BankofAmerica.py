import requests
import json
import time
from save_job import save_job
from database import get_connection


COMPANY_NAME = "Bank of America"
COMPANY_LOGO = "https://img.logo.dev/bankofamerica.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://careers.bankofamerica.com"
API_URL = BASE_URL + "/services/jobssearchservlet"
OUTPUT_FILE = "bank_of_america_india_jobs.json"


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


def detect_experience(title, category):
    text = f"{title or ''} {category or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "graduate" in text or "fresher" in text or "entry level" in text:
        return "Freshers"

    if "analyst" in text or "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text or "avp" in text:
        return "3+ yrs"

    if (
        "manager" in text
        or "lead" in text
        or "vp" in text
        or "vice president" in text
        or "director" in text
    ):
        return "5+ yrs"

    return "Not specified"


def fetch_boa_india_jobs():

    session = requests.Session()

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://careers.bankofamerica.com/en-us/job-search/india"
    }

    session.headers.update(headers)

    all_jobs = []
    seen_ids = set()

    conn = get_connection()
    cur = conn.cursor()

    start = 0
    batch_size = 10
    max_pages = 15

    print(f"Started fetching {COMPANY_NAME} India jobs...")

    try:

        for page in range(max_pages):

            rows = start + batch_size

            print(f"\nScraping {COMPANY_NAME} — start={start}, rows={rows}")

            params = {
                "start": start,
                "rows": rows,
                "search": "jobsByLocation",
                "searchstring": "India"
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

            jobs = data.get("jobsList", [])

            if not jobs:
                break

            new_found = 0

            for job in jobs:

                job_id = job.get("jobRequisitionId")

                if not job_id or job_id in seen_ids:
                    continue

                seen_ids.add(job_id)
                new_found += 1

                title = (job.get("postingTitle") or "").strip()
                location = (job.get("location") or "").strip()

                link_part = (job.get("jcrURL") or "").strip()

                if not link_part:
                    continue

                apply_link = BASE_URL + link_part

                posted_at = job.get("datePosted")
                category = job.get("jobCategory")
                employment_type = job.get("employmentType")

                keywords = list(set([
                    job_id,
                    posted_at,
                    category,
                    employment_type
                ]))

                keywords = [k for k in keywords if k]

                job_description = (
                    job.get("jobDescription")
                    or job.get("description")
                    or job.get("shortDescription")
                    or ""
                )

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title or "Not Mentioned",
                    "location": location or "India",
                    "apply_link": apply_link,
                    "keywords": keywords,

                    "source": "Bank of America Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location),
                    "job_type": detect_job_type(title, employment_type),
                    "experience": detect_experience(title, category),
                    "education": "Not specified",
                    "department": category,
                    "salary": "Not disclosed",
                    "job_description": job_description,
                    "company_description": "Bank of America is a global financial services company providing banking, investment and technology services.",
                    "posted_at": posted_at
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            if new_found == 0:
                break

            start += batch_size
            time.sleep(1)

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

    jobs = fetch_boa_india_jobs()

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