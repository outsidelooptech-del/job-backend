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

COMPANY_NAME = "Uber"
COMPANY_LOGO = "https://img.logo.dev/uber.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

URL = "https://www.uber.com/api/loadSearchJobsResults?localeCode=en"

OUTPUT_FILE = "uber_india_jobs.json"

MAX_JOBS = 500

scraper = cloudscraper.create_scraper()

HEADERS = {
    "accept": "*/*",
    "content-type": "application/json",
    "origin": "https://www.uber.com",
    "referer": "https://www.uber.com/in/en/careers/list/",
    "user-agent": "Mozilla/5.0",
    "x-csrf-token": "x"
}


# =============================
# HELPERS
# =============================

def detect_work_mode(location, title="", time_type=""):
    text = f"{location or ''} {title or ''} {time_type or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, time_type=""):
    text = f"{title or ''} {time_type or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def detect_experience(title, level=""):
    text = f"{title or ''} {level or ''}".lower()

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

    return level if level else "Not specified"


# =============================
# SCRAPER
# =============================

def scrape_uber_jobs():

    conn = psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )

    cur = conn.cursor()

    all_jobs = []

    seen_ids = set()
    seen_links = set()

    page = 0

    print("🚀 Scraping Uber India jobs...\n")

    try:

        while len(all_jobs) < MAX_JOBS:

            print(f"\nFetching page {page}")

            payload = {
                "limit": 10,
                "page": page,
                "params": {
                    "location": [
                        {
                            "country": "IND",
                            "city": "Bangalore"
                        },
                        {
                            "country": "IND",
                            "city": "Hyderabad"
                        },
                        {
                            "country": "IND",
                            "city": "Gurgaon"
                        }
                    ]
                }
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

            try:
                data = response.json()
            except Exception:
                print("Invalid JSON response.")
                break

            jobs = []

            if isinstance(data.get("data"), list):
                jobs = data["data"]

            elif isinstance(data.get("data"), dict):

                possible_paths = [
                    ["data", "searchJobs", "jobs"],
                    ["data", "jobs"],
                    ["data", "results"]
                ]

                for path in possible_paths:

                    temp = data

                    for key in path:
                        temp = temp.get(key, {})

                    if isinstance(temp, list):
                        jobs = temp
                        break

            if not jobs:
                print("No more jobs found.")
                break

            for job in jobs:

                if len(all_jobs) >= MAX_JOBS:
                    break

                job_id = str(job.get("id", "")).strip()

                if not job_id:
                    continue

                apply_link = (
                    f"https://www.uber.com/careers/list/{job_id}/"
                )

                if job_id in seen_ids or apply_link in seen_links:
                    continue

                seen_ids.add(job_id)
                seen_links.add(apply_link)

                location_data = job.get("location", {})

                city = location_data.get("city", "")
                country_name = location_data.get("countryName", "")

                location = ", ".join(
                    filter(None, [city, country_name])
                ) or "India"

                department = job.get("department")
                team = job.get("team")
                level = job.get("level")
                time_type = job.get("timeType")
                creation_date = job.get("creationDate")
                updated_date = job.get("updatedDate")

                keywords = list(set([
                    str(k)
                    for k in [
                        department,
                        team,
                        country_name,
                        level,
                        time_type,
                        creation_date,
                        updated_date,
                        f"Page {page}"
                    ]
                    if k
                ]))

                title = job.get("title") or "Not Mentioned"

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": keywords,

                    "source": "Uber Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(
                        location,
                        title,
                        time_type
                    ),
                    "job_type": detect_job_type(
                        title,
                        time_type
                    ),
                    "experience": detect_experience(
                        title,
                        level
                    ),
                    "education": "Not specified",
                    "department": department or "Not specified",
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "Uber is a global technology platform providing ride-sharing, food delivery, freight, logistics, and mobility services.",
                    "posted_at": creation_date or updated_date or "Not specified"
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            print("Jobs collected:", len(all_jobs))

            page += 1

            time.sleep(1)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Uber jobs to database.")

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

    jobs = scrape_uber_jobs()

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