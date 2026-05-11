import requests
import json
from save_job import save_job
from database import get_connection


# ----------------------------
# CONFIG
# ----------------------------

COMPANY_NAME = "Mphasis"
COMPANY_LOGO = "https://img.logo.dev/mphasis.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

URL = "https://mphasis.ripplehire.com/candidate/candidatejobsearch"
TOKEN = "ty4DfyWddnOrtpclQeia"
OUTPUT_FILE = "mphasis_jobs.json"

HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://mphasis.ripplehire.com",
    "referer": "https://mphasis.ripplehire.com/",
    "user-agent": "Mozilla/5.0",
    "x-requested-with": "XMLHttpRequest"
}


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


def normalize_experience(experience, title=""):
    text = f"{experience or ''} {title or ''}".lower()

    if "intern" in text or "trainee" in text:
        return "Internship"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if experience:
        return str(experience)

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "manager" in text or "lead" in text or "architect" in text:
        return "5+ yrs"

    return "Not specified"


# ----------------------------
# SCRAPER
# ----------------------------

def scrape_mphasis_jobs():

    conn = get_connection()
    cur = conn.cursor()

    all_jobs = []
    page = 0
    page_size = 10
    seen_ids = set()

    print("🚀 Fetching Mphasis jobs...\n")

    try:
        while True:

            payload = {
                "careerSiteUrlParams": json.dumps({
                    "page": page,
                    "search": "*:*",
                    "token": TOKEN,
                    "source": "CAREERSITE",
                    "pagesize": page_size,
                    "location": "Bangalore+Hyderabad+Mangalore+Mumbai+Pune",
                    "exp": "",
                    "function": ""
                }),
                "lang": "en"
            }

            try:
                response = requests.post(
                    URL,
                    headers=HEADERS,
                    data=payload,
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

            jobs = data.get("jobVoList", [])
            total_jobs = data.get("totalJobCount", 0)

            if not jobs:
                break

            print(f"Processing page {page}")

            new_found = 0

            for job in jobs:

                title = job.get("jobTitle") or "Not Mentioned"
                location = job.get("locations") or "India"
                experience = job.get("jobReqExp")
                job_seq = job.get("jobSeq")

                if not job_seq:
                    continue

                if job_seq in seen_ids:
                    continue

                seen_ids.add(job_seq)
                new_found += 1

                apply_link = (
                    f"https://mphasis.ripplehire.com/candidate/"
                    f"?token={TOKEN}&source=CAREERSITE#detail/job/{job_seq}"
                )

                department = (
                    job.get("function")
                    or job.get("jobFunction")
                    or job.get("department")
                    or job.get("vertical")
                )

                job_description = (
                    job.get("jobDescription")
                    or job.get("description")
                    or job.get("jobDesc")
                    or ""
                )

                posted_at = (
                    job.get("postedDate")
                    or job.get("createdDate")
                    or job.get("modifiedDate")
                )

                keywords = [
                    experience,
                    department,
                    job_seq,
                    posted_at
                ]

                keywords = [k for k in keywords if k]

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": list(set(keywords)),

                    "source": "Mphasis RippleHire API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title),
                    "experience": normalize_experience(experience, title),
                    "education": "Not specified",
                    "department": department,
                    "salary": "Not disclosed",
                    "job_description": job_description,
                    "company_description": "Mphasis is a global IT services and digital transformation company.",
                    "posted_at": posted_at
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            if new_found == 0:
                print("No new jobs found. Stopping.")
                break

            page += 1

            if page * page_size >= total_jobs:
                break

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Mphasis jobs to database.")

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

    jobs_data = scrape_mphasis_jobs()

    print("\n✅ Total Jobs Collected:", len(jobs_data))

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