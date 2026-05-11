import requests
import json
from save_job import save_job
from database import get_connection


COMPANY_NAME = "HCLTech"
COMPANY_LOGO = "https://img.logo.dev/hcltech.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://careers.hcltech.com"
JOBS_API = "https://careers.hcltech.com/services/recruiting/v1/jobs"
OUTPUT_FILE = "hcltech_jobs.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://careers.hcltech.com",
    "Referer": "https://careers.hcltech.com/search/"
}


def detect_work_mode(location, title=""):
    text = f"{location or ''} {title or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, employment_type=""):
    text = f"{title or ''} {employment_type or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return employment_type or "Full Time"


def detect_experience(title):
    text = (title or "").lower()

    if "intern" in text:
        return "Internship"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if "associate" in text or "junior" in text or "trainee" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "manager" in text or "lead" in text or "architect" in text:
        return "5+ yrs"

    return "Not specified"


def scrape_hcl_jobs():

    session = requests.Session()

    try:
        session.get(
            BASE_URL,
            headers=HEADERS,
            timeout=30
        )
    except Exception:
        pass

    max_pages = 50
    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    print("\n🚀 HCLTech Job Scraper Started...\n")

    try:
        for page in range(max_pages):

            payload = {
                "locale": "en_US",
                "pageNumber": page,
                "sortBy": "",
                "keywords": "",
                "location": "",
                "alertId": "",
                "brand": "",
                "categoryId": 0,
                "facetFilters": {
                    "custCountryRegion": ["India"]
                },
                "rcmCandidateId": "",
                "skills": []
            }

            try:
                response = session.post(
                    JOBS_API,
                    headers=HEADERS,
                    json=payload,
                    timeout=30
                )
            except Exception as e:
                print("Request error:", e)
                break

            if response.status_code != 200:
                print("Request failed at page:", page)
                break

            try:
                data = response.json()
            except ValueError:
                print("Invalid JSON response.")
                break

            jobs = data.get("jobSearchResult", [])

            if not jobs:
                print("🚫 No more jobs found.")
                break

            print(f"\n========== PAGE {page} ==========")

            new_found = 0

            for job in jobs:

                try:
                    info = job.get("response", {})

                    job_id = info.get("id")
                    title = info.get("unifiedStandardTitle") or info.get("title")
                    city = info.get("custprimecity") or info.get("city")
                    url_title = info.get("urlTitle")

                    job_url = (
                        f"https://careers.hcltech.com/job/{url_title}/{job_id}-en_US"
                        if job_id and url_title else ""
                    )

                    if not job_url:
                        continue

                    if job_url in seen_links:
                        continue

                    seen_links.add(job_url)
                    new_found += 1

                    job_family = info.get("unifiedJobFamily")
                    employment_type = info.get("employmentType")
                    posted_at = (
                        info.get("postedDate")
                        or info.get("datePosted")
                        or info.get("postingDate")
                    )

                    job_description = (
                        info.get("jobDescription")
                        or info.get("description")
                        or info.get("externalJobDescription")
                        or ""
                    )

                    keywords = [
                        job_id,
                        job_family,
                        employment_type,
                        posted_at
                    ]

                    keywords = [k for k in keywords if k]

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title or "Not Mentioned",
                        "location": city or "India",
                        "apply_link": job_url,
                        "keywords": list(set(keywords)),

                        "source": "HCLTech Careers API",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(city, title),
                        "job_type": detect_job_type(title, employment_type),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": job_family,
                        "salary": "Not disclosed",
                        "job_description": job_description,
                        "company_description": "HCLTech is a global technology company providing digital, engineering, cloud, AI and IT services.",
                        "posted_at": posted_at
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping job:", e)

            if new_found == 0:
                print("No new jobs found. Stopping.")
                break

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} HCLTech jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs_data = scrape_hcl_jobs()

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