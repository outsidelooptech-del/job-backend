import requests
import json
import re
from save_job import save_job
from database import get_connection


# ----------------------------
# CONFIG
# ----------------------------

COMPANY_NAME = "Ericsson"
COMPANY_LOGO = "https://img.logo.dev/ericsson.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://jobs.ericsson.com/api/pcsx/search"
OUTPUT_FILE = "ericsson_india_jobs.json"


def clean_department(dept):
    if not dept:
        return ""
    return re.sub(r"^\d+\s*", "", str(dept)).strip()


def detect_work_mode(remote_indicator, locations):
    text = f"{remote_indicator or ''} {locations or ''}".lower()

    if "remote" in text or remote_indicator == "1":
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, job_type, worker_type):
    text = f"{title or ''} {job_type or ''} {worker_type or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return job_type or worker_type or "Full Time"


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
        or "architect" in text
        or "principal" in text
    ):
        return "5+ yrs"

    return "Not specified"


def fetch_jobs(start=0, limit=10):

    params = {
        "domain": "ericsson.com",
        "query": "",
        "location": "India",
        "start": start,
        "sort_by": "distance",
        "filter_include_remote": 1
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    response = requests.get(
        BASE_URL,
        params=params,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data.get("data", {}).get("positions", [])


# ----------------------------
# SCRAPER
# ----------------------------

def scrape_all_jobs(limit=10, max_pages=50):

    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    print("\n🚀 Ericsson India Job Scraper Started...\n")

    try:

        for page in range(1, max_pages + 1):

            start = (page - 1) * limit

            print(f"\n📌 Fetching Page {page} | Start={start}")

            try:
                jobs = fetch_jobs(start=start, limit=limit)
            except Exception as e:
                print("Request failed:", e)
                break

            if not jobs:
                print("🚫 No more jobs available.")
                break

            jobs_found = 0

            for job in jobs:

                try:
                    title = job.get("name") or "Not Mentioned"

                    department = clean_department(job.get("department"))

                    locations = ", ".join(job.get("locations", []))

                    position_url = job.get("positionUrl")

                    if not position_url:
                        continue

                    apply_link = "https://jobs.ericsson.com" + position_url

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    job_type_raw = job.get("jobType")
                    worker_type = job.get("workerType")
                    remote_indicator = job.get("remoteIndicator")
                    display_job_id = job.get("displayJobId")

                    keywords = [
                        display_job_id,
                        department,
                        job_type_raw,
                        worker_type,
                        remote_indicator,
                        locations
                    ]

                    keywords = [k for k in keywords if k]

                    job_description = (
                        job.get("description")
                        or job.get("jobDescription")
                        or ""
                    )

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title,
                        "location": locations or "India",
                        "apply_link": apply_link,
                        "keywords": list(set(keywords)),

                        "source": "Ericsson Careers API",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(remote_indicator, locations),
                        "job_type": detect_job_type(title, job_type_raw, worker_type),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": department or None,
                        "salary": "Not disclosed",
                        "job_description": job_description,
                        "company_description": "Ericsson is a global telecommunications and networking company providing 5G, cloud, IoT and connectivity solutions.",
                        "posted_at": job.get("postedDate") or job.get("datePosted")
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                    jobs_found += 1

                except Exception as e:
                    print("Skipping job:", e)

            if jobs_found == 0:
                print("No jobs parsed. Stopping.")
                break

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Ericsson jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal Error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


# ----------------------------
# MAIN RUN
# ----------------------------

if __name__ == "__main__":

    jobs_data = scrape_all_jobs(limit=10, max_pages=100)

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