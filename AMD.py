import requests
import json
import time
from database import get_connection
from save_job import save_job


COMPANY_NAME = "AMD"
COMPANY_LOGO = "https://img.logo.dev/amd.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://careers.amd.com/api/jobs"


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


def detect_experience(title):
    if not title:
        return "Not specified"

    text = title.lower()

    if "intern" in text:
        return "Internship"

    if "graduate" in text or "fresher" in text or "entry level" in text:
        return "Freshers"

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "staff" in text or "principal" in text or "lead" in text or "manager" in text:
        return "5+ yrs"

    return "Not specified"


def fetch_amd_india_jobs():

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    params = {
        "categories": "Engineering",
        "location": "India",
        "stretch": "10",
        "stretchUnit": "MILES",
        "sortBy": "relevance",
        "descending": "false",
        "internal": "false",
    }

    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    try:
        page = 1
        max_pages = 100

        print("Started fetching AMD India jobs...")

        while page <= max_pages:

            print(f"Scraping {COMPANY_NAME} India jobs — page {page}")

            params["page"] = page

            try:
                response = requests.get(
                    BASE_URL,
                    headers=headers,
                    params=params,
                    timeout=30
                )
            except Exception as e:
                print("Request error:", e)
                break

            if response.status_code != 200:
                print("Request failed. Stopping.")
                break

            try:
                data = response.json()
            except ValueError:
                print("Invalid JSON response.")
                break

            jobs = data.get("jobs", [])

            if not jobs:
                print("No more jobs found.")
                break

            new_found = 0

            for job in jobs:

                info = job.get("data", {})

                title = (info.get("title") or "").strip()
                location = (info.get("short_location") or "").strip()
                apply_link = (info.get("apply_url") or "").strip()

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)
                new_found += 1

                posted_at = info.get("posted_date")
                employment_type = info.get("employment_type")
                department = info.get("department")
                req_id = info.get("req_id")

                job_description = (
                    info.get("description")
                    or info.get("job_description")
                    or info.get("description_html")
                    or ""
                )

                keywords = []

                if posted_at:
                    keywords.append(posted_at)

                if employment_type:
                    keywords.append(employment_type)

                if department:
                    keywords.append(department)

                if req_id:
                    keywords.append(req_id)

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title or "Not Mentioned",
                    "location": location or "India",
                    "apply_link": apply_link,
                    "keywords": list(set([k for k in keywords if k])),

                    "source": "AMD Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location),
                    "job_type": detect_job_type(title, employment_type),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": department,
                    "salary": "Not disclosed",
                    "job_description": job_description,
                    "company_description": "AMD is a global semiconductor company that develops high-performance computing and graphics technologies.",
                    "posted_at": posted_at
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            if new_found == 0:
                break

            page += 1
            time.sleep(0.5)

        conn.commit()

        print("Finished saving AMD jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs = fetch_amd_india_jobs()

    with open("amd_india_jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Total {COMPANY_NAME} India jobs scraped: {len(jobs)}")
    print("Saved to amd_india_jobs.json")