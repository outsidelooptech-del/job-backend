import requests
import json
import time
from database import get_connection
from save_job import save_job


COMPANY_NAME = "Airbus"
COMPANY_LOGO = "https://img.logo.dev/airbus.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://ag.wd3.myworkdayjobs.com"
CAREER_PAGE = BASE_URL + "/Airbus"
API_URL = BASE_URL + "/wday/cxs/ag/Airbus/jobs"

INDIA_ID = "c4f78be1a8f14da0ab49ce1162348a5e"


def detect_work_mode(location, bullet_fields=None):
    text = f"{location or ''} {' '.join(bullet_fields or [])}".lower()

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

    if "temporary" in text:
        return "Temporary"

    return "Full Time"


def detect_experience(title, bullet_fields=None):
    text = f"{title or ''} {' '.join(bullet_fields or [])}".lower()

    if "intern" in text:
        return "Internship"

    if "graduate" in text or "fresher" in text or "entry level" in text:
        return "Freshers"

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "manager" in text or "lead" in text or "architect" in text:
        return "5+ yrs"

    return "Not specified"


def fetch_airbus_india_jobs():

    session = requests.Session()

    session.get(
        CAREER_PAGE,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": BASE_URL,
        "Referer": CAREER_PAGE + "?locationCountry=" + INDIA_ID,
        "User-Agent": "Mozilla/5.0"
    }

    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    offset = 0
    limit = 20
    total = None

    print("Started fetching Airbus India jobs...")

    try:

        while True:

            print(f"\nFetching {COMPANY_NAME} offset {offset}...")

            payload = {
                "appliedFacets": {
                    "locationCountry": [INDIA_ID]
                },
                "limit": limit,
                "offset": offset,
                "searchText": ""
            }

            try:
                response = session.post(
                    API_URL,
                    headers=headers,
                    json=payload,
                    timeout=30
                )
            except Exception as e:
                print("Request error:", e)
                break

            if response.status_code != 200:
                print("Request Failed:", response.status_code)
                break

            try:
                data = response.json()
            except ValueError:
                print("Invalid JSON response")
                break

            if total is None:
                total = data.get("total", 0)

            jobs = data.get("jobPostings", [])

            if not jobs:
                break

            for job in jobs:

                title = (job.get("title") or "").strip()
                location = (job.get("locationsText") or "").strip()
                external_path = (job.get("externalPath") or "").strip()

                apply_link = CAREER_PAGE + external_path if external_path else ""

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)

                bullet_fields = job.get("bulletFields", []) or []
                posted_on = job.get("postedOn")

                keywords = list(filter(None, [
                    posted_on,
                    *bullet_fields
                ]))

                department = None

                if bullet_fields:
                    department = bullet_fields[0]

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title or "Not Mentioned",
                    "location": location or "Not Mentioned",
                    "apply_link": apply_link,
                    "keywords": list(set(keywords)),

                    "source": "Airbus Workday",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, bullet_fields),
                    "job_type": detect_job_type(title, bullet_fields),
                    "experience": detect_experience(title, bullet_fields),
                    "education": "Not specified",
                    "department": department,
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "Airbus is a global aerospace company specializing in commercial aircraft, helicopters, defence, space and related services.",
                    "posted_at": posted_on
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            print(f"Collected: {len(all_jobs)} / {total}")

            offset += limit

            if total and offset >= total:
                break

            time.sleep(1)

        conn.commit()

        print("Finished saving Airbus jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs = fetch_airbus_india_jobs()

    print(f"\nTotal {COMPANY_NAME} India Jobs: {len(jobs)}")

    with open("airbus_india_jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)

    print("Saved to airbus_india_jobs.json")