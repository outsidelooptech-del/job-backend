import requests
import json
from save_job import save_job
from database import get_connection


COMPANY_NAME = "Flipkart"
COMPANY_LOGO = "https://img.logo.dev/flipkart.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

URL = "https://public.zwayam.com/jobs/search"
OUTPUT_FILE = "flipkart_jobs.json"

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "origin": "https://www.flipkartcareers.com",
    "referer": "https://www.flipkartcareers.com/",
    "user-agent": "Mozilla/5.0",
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

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def normalize_experience(exp, title=""):
    text = f"{exp or ''} {title or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if exp:
        return exp

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "manager" in text or "lead" in text:
        return "5+ yrs"

    return "Not specified"


def scrape_flipkart_jobs():

    jobs = []
    seen_links = set()

    start = 0
    page_size = 10
    max_jobs = 500

    conn = get_connection()
    cur = conn.cursor()

    print("\n🚀 Flipkart Job Scraper Started...\n")

    try:
        while len(jobs) < max_jobs:

            payload = {
                "filterCri": json.dumps({
                    "paginationStartNo": start,
                    "selectedCall": "sort",
                    "sortCriteria": {
                        "name": "modifiedDate",
                        "isAscending": False
                    },
                    "anyOfTheseWords": ""
                }),
                "domain": "www.flipkartcareers.com",
                "companyId": "MTUxMTA="
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

            print("Status Code:", response.status_code)

            if response.status_code != 200:
                break

            try:
                data = response.json()
            except ValueError:
                print("Invalid JSON response.")
                break

            job_list = data.get("data", {}).get("data", [])

            if not job_list:
                print("🚫 No more jobs found.")
                break

            print(f"Scraping page starting at {start}... Found {len(job_list)} jobs")

            new_found = 0

            for job in job_list:

                if len(jobs) >= max_jobs:
                    break

                source = job.get("_source", {})

                title = source.get("jobTitle")
                location = source.get("location")
                job_url = source.get("jobUrl")
                job_id = source.get("id")

                if not job_url or not job_id:
                    continue

                apply_link = (
                    f"https://www.flipkartcareers.com/flipkart/jobview/"
                    f"{job_url}?id={job_id}"
                )

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)
                new_found += 1

                experience = source.get("experienceUIField")
                job_code = source.get("jobCode")
                department = (
                    source.get("department")
                    or source.get("functionalArea")
                    or source.get("category")
                )

                job_description = (
                    source.get("jobDescription")
                    or source.get("description")
                    or source.get("jobDetails")
                    or ""
                )

                posted_at = (
                    source.get("modifiedDate")
                    or source.get("createdDate")
                    or source.get("postedDate")
                )

                keywords = [
                    experience,
                    job_code,
                    department
                ]

                keywords = [k for k in keywords if k]

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title or "Not Mentioned",
                    "location": location or "India",
                    "apply_link": apply_link,
                    "keywords": list(set(keywords)),

                    "source": "Flipkart Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title),
                    "experience": normalize_experience(experience, title),
                    "education": "Not specified",
                    "department": department,
                    "salary": "Not disclosed",
                    "job_description": job_description,
                    "company_description": "Flipkart is one of India's leading e-commerce companies, offering technology, marketplace, logistics and digital commerce services.",
                    "posted_at": posted_at
                }

                jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            if new_found == 0:
                print("No new jobs found. Stopping.")
                break

            start += page_size

        conn.commit()

        print(f"\n✅ Saved {len(jobs)} Flipkart jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return jobs


if __name__ == "__main__":

    jobs_data = scrape_flipkart_jobs()

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