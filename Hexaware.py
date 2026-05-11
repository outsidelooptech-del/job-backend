import requests
import json
from save_job import save_job
from database import get_connection


COMPANY_NAME = "Hexaware"
COMPANY_LOGO = "https://img.logo.dev/hexaware.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_API = "https://fa-etqo-saasfaprod1.fa.ocs.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
OUTPUT_FILE = "hexaware_india_jobs.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "ora-irc-language": "en"
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


def scrape_jobs():

    limit = 25
    offset = 0
    max_jobs = 500

    total_jobs = 0
    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    print("\n🚀 Hexaware Job Scraper Started...\n")

    try:
        while total_jobs < max_jobs:

            finder_value = (
                "findReqs;"
                "siteNumber=CX_1,"
                "facetsList=LOCATIONS;WORK_LOCATIONS;WORKPLACE_TYPES;TITLES;CATEGORIES;ORGANIZATIONS;POSTING_DATES;FLEX_FIELDS,"
                f"limit={limit},"
                "lastSelectedFacet=LOCATIONS,"
                "selectedLocationsFacet=300000000446279,"
                "selectedPostingDatesFacet=30,"
                "sortBy=POSTING_DATES_DESC"
            )

            params = {
                "onlyData": "true",
                "offset": offset,
                "expand": "requisitionList.workLocation",
                "finder": finder_value
            }

            try:
                response = requests.get(
                    BASE_API,
                    headers=HEADERS,
                    params=params,
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

            items = data.get("items", [])

            if not items:
                break

            requisitions = items[0].get("requisitionList", [])

            if not requisitions:
                break

            print(f"\n===== Offset {offset} =====")

            new_found = 0

            for job in requisitions:

                if total_jobs >= max_jobs:
                    break

                job_id = job.get("Id")
                title = job.get("Title") or "Not Mentioned"

                work_loc = job.get("workLocation") or []
                town = work_loc[0].get("TownOrCity", "") if work_loc else ""

                apply_link = (
                    f"https://jobs.hexaware.com/#en/sites/CX_1/jobs/preview/{job_id}/"
                    "?lastSelectedFacet=LOCATIONS"
                    "&selectedLocationsFacet=300000000446279"
                    "&selectedPostingDatesFacet=30"
                ) if job_id else ""

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)
                new_found += 1

                job_family = job.get("JobFamily")
                employment_type = job.get("EmploymentType")
                posted_at = (
                    job.get("PostingDate")
                    or job.get("PostedDate")
                    or job.get("CreationDate")
                )

                keywords = [
                    job_id,
                    job_family,
                    employment_type,
                    posted_at
                ]

                keywords = [k for k in keywords if k]

                job_description = (
                    job.get("ExternalDescriptionStr")
                    or job.get("Description")
                    or job.get("JobDescription")
                    or ""
                )

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": town or "India",
                    "apply_link": apply_link,
                    "keywords": list(set(keywords)),

                    "source": "Hexaware Oracle Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(town, title),
                    "job_type": detect_job_type(title, employment_type),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": job_family,
                    "salary": "Not disclosed",
                    "job_description": job_description,
                    "company_description": "Hexaware is a global IT services and digital transformation company.",
                    "posted_at": posted_at
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

                total_jobs += 1

            if new_found == 0:
                print("No new jobs found. Stopping.")
                break

            offset += limit

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Hexaware jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs_data = scrape_jobs()

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