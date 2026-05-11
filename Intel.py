import requests
import json
import time

from save_job import save_job
from database import get_connection


COMPANY_NAME = "Intel"
COMPANY_LOGO = "https://img.logo.dev/intel.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://intel.wd1.myworkdayjobs.com"
API_URL = f"{BASE_URL}/wday/cxs/intel/External/jobs"
OUTPUT_FILE = "intel_jobs.json"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
}

LOCATION_FACETS = [
    "1e4a4eb3adf101ab560f6577bf81eacf",
    "1e4a4eb3adf1015ff0865f77bf81e5cf",
    "1e4a4eb3adf101fec7c50d79bf814fd1",
    "1e4a4eb3adf101f44070f976bf8184cf"
]

LIMIT_PER_REQUEST = 20
MAX_JOBS = 500


def detect_work_mode(location, title=""):
    text = f"{location or ''} {title or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, bullet_fields=None):
    text = f"{title or ''} {' '.join(bullet_fields or [])}".lower()

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

    if "graduate" in text or "fresher" in text or "entry level" in text:
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
        or "staff" in text
    ):
        return "5+ yrs"

    return "Not specified"


def scrape_intel_jobs():

    all_jobs = []
    seen_links = set()
    offset = 0

    conn = get_connection()
    cur = conn.cursor()

    print("🚀 Intel Job Scraper Started...\n")

    try:
        while len(all_jobs) < MAX_JOBS:

            payload = {
                "appliedFacets": {
                    "locations": LOCATION_FACETS
                },
                "limit": LIMIT_PER_REQUEST,
                "offset": offset,
                "searchText": ""
            }

            try:
                response = requests.post(
                    API_URL,
                    json=payload,
                    headers=HEADERS,
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
                print("Invalid JSON response.")
                break

            jobs = data.get("jobPostings", [])

            if not jobs:
                break

            print(f"Fetched {len(jobs)} jobs (offset {offset})")

            new_found = 0

            for job in jobs:

                if len(all_jobs) >= MAX_JOBS:
                    break

                title = job.get("title") or "Not Mentioned"
                location = job.get("locationsText") or "India"
                posted_at = job.get("postedOn")
                external_path = job.get("externalPath")

                apply_link = (
                    f"{BASE_URL}/en-US/External{external_path}"
                    if external_path else ""
                )

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)
                new_found += 1

                bullet_fields = job.get("bulletFields", []) or []

                job_id = bullet_fields[0] if bullet_fields else None
                department = bullet_fields[1] if len(bullet_fields) > 1 else None

                keywords = [
                    job_id,
                    posted_at,
                    department,
                    *bullet_fields
                ]

                keywords = [k for k in keywords if k]

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": list(set(keywords)),

                    "source": "Intel Workday",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title, bullet_fields),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": department,
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "Intel is a global semiconductor company known for processors, chips, AI, cloud, data center and computing technologies.",
                    "posted_at": posted_at
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            if new_found == 0:
                break

            offset += LIMIT_PER_REQUEST
            time.sleep(1)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Intel jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs_data = scrape_intel_jobs()

    print("\n✅ Total Jobs Scraped:", len(jobs_data))

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

    print("\n📂 Saved Successfully:", OUTPUT_FILE)