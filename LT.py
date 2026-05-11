import requests
import json
import time

from save_job import save_job
from database import get_connection


# ----------------------------
# CONFIG
# ----------------------------

COMPANY_NAME = "Larsen & Toubro"
COMPANY_LOGO = "https://img.logo.dev/larsentoubro.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://larsentoubrocareers.peoplestrong.com/api/cp/rest/altone/cp/jobs/v1"
OUTPUT_FILE = "lnt_jobs.json"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://larsentoubrocareers.peoplestrong.com",
    "Referer": "https://larsentoubrocareers.peoplestrong.com/job/joblist",
    "User-Agent": "Mozilla/5.0"
}


# ----------------------------
# HELPERS
# ----------------------------

def detect_work_mode(location, title=""):
    text = f"{location or ''} {title or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title):
    text = (title or "").lower()

    if "intern" in text or "trainee" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def normalize_experience(exp, title=""):
    text = f"{exp or ''} {title or ''}".lower()

    if "intern" in text or "trainee" in text:
        return "Internship"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if exp:
        return str(exp)

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "manager" in text or "lead" in text or "head" in text:
        return "5+ yrs"

    return "Not specified"


# ----------------------------
# SCRAPER
# ----------------------------

def scrape_lnt_jobs():

    conn = get_connection()
    cur = conn.cursor()

    all_jobs = []
    seen_links = set()

    offset = 0
    limit = 45

    print("🚀 Fetching L&T jobs...\n")

    try:
        try:
            first_response = requests.post(
                BASE_URL,
                headers=HEADERS,
                json={
                    "offset": 0,
                    "limit": limit
                },
                timeout=30
            )
        except Exception as e:
            print("Initial request error:", e)
            return []

        if first_response.status_code != 200:
            print("Initial request failed:", first_response.status_code)
            return []

        try:
            data = first_response.json()
        except ValueError:
            print("Invalid JSON response.")
            return []

        total_records = data.get("totalRecords", 0)

        print("Total Records:", total_records)

        while offset < total_records:

            payload = {
                "offset": offset,
                "limit": limit
            }

            try:
                response = requests.post(
                    BASE_URL,
                    headers=HEADERS,
                    json=payload,
                    timeout=30
                )
            except Exception as e:
                print("Request error:", e)
                break

            if response.status_code != 200:
                print("Failed:", response.status_code)
                break

            try:
                data = response.json()
            except ValueError:
                print("Invalid JSON response.")
                break

            jobs = data.get("response", [])

            if not jobs:
                print("No more jobs found.")
                break

            new_found = 0

            for job in jobs:

                job_title = job.get("jobTitle") or "Not Mentioned"
                location = job.get("locationHierarchy") or "India"
                apply_link = job.get("jobDetailUrl")

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)
                new_found += 1

                exp_range = job.get("expRange")
                ctc_range = job.get("CTCRange")
                openings = job.get("openings")
                posted_at = job.get("jobPostedDate")
                closure_date = job.get("jobClosureDate")

                department = (
                    job.get("jobFunction")
                    or job.get("functionalArea")
                    or job.get("department")
                    or job.get("category")
                )

                job_description = (
                    job.get("jobDescription")
                    or job.get("description")
                    or job.get("jobDetail")
                    or ""
                )

                keywords = [
                    exp_range,
                    ctc_range,
                    openings,
                    posted_at,
                    closure_date,
                    department
                ]

                keywords = [k for k in keywords if k]

                job_data = {
                    "company": COMPANY_NAME,
                    "title": job_title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": list(set(keywords)),

                    "source": "Larsen & Toubro PeopleStrong API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, job_title),
                    "job_type": detect_job_type(job_title),
                    "experience": normalize_experience(exp_range, job_title),
                    "education": "Not specified",
                    "department": department,
                    "salary": ctc_range or "Not disclosed",
                    "job_description": job_description,
                    "company_description": "Larsen & Toubro is a major Indian multinational company operating in engineering, construction, manufacturing, technology and financial services.",
                    "posted_at": posted_at
                }

                all_jobs.append(job_data)

                print("Saving:", job_title)

                save_job(job_data, cur)

            if new_found == 0:
                print("No new jobs found. Stopping.")
                break

            offset += limit

            print(f"Fetched {offset} / {total_records}")

            time.sleep(1)

        conn.commit()

        print("✅ Finished saving to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


# ----------------------------
# MAIN
# ----------------------------

if __name__ == "__main__":

    jobs_data = scrape_lnt_jobs()

    print("\nTotal Jobs Collected:", len(jobs_data))

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