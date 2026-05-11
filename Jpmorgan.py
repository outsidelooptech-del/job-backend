import requests
import json

from save_job import save_job
from database import get_connection


COMPANY_NAME = "JPMorgan Chase & Co."
COMPANY_LOGO = "https://img.logo.dev/jpmorganchase.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_API = "https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
OUTPUT_FILE = "jpmc_jobs.json"

HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

SITE_NUMBER = "CX_1001"
LOCATION_ID = "300000000289360"

MAX_JOBS = 500
PAGE_SIZE = 25


def detect_work_mode(location, title=""):
    text = f"{location or ''} {title or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, job_family="", job_function=""):
    text = f"{title or ''} {job_family or ''} {job_function or ''}".lower()

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

    if "analyst" in text or "associate" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if (
        "manager" in text
        or "lead" in text
        or "vice president" in text
        or "vp" in text
        or "director" in text
    ):
        return "5+ yrs"

    return "Not specified"


def scrape_jpmc_jobs():

    jobs = []
    seen_links = set()
    offset = 0

    conn = get_connection()
    cur = conn.cursor()

    print("🚀 Fetching JPMorgan jobs...\n")

    try:
        while len(jobs) < MAX_JOBS:

            finder = (
                f"findReqs;siteNumber={SITE_NUMBER},"
                f"facetsList=LOCATIONS%3BWORK_LOCATIONS%3BWORKPLACE_TYPES%3B"
                f"POSTING_DATES%3BJOB_FUNCTIONS%3BJOB_FAMILIES,"
                f"limit={PAGE_SIZE},"
                f"offset={offset},"
                f"locationId={LOCATION_ID},"
                f"sortBy=POSTING_DATES_DESC"
            )

            params = {
                "onlyData": "true",
                "expand": "requisitionList.workLocation,requisitionList.otherWorkLocations",
                "finder": finder
            }

            print(f"Fetching offset {offset}")

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

            new_found = 0

            for job in requisitions:

                if len(jobs) >= MAX_JOBS:
                    break

                job_id = job.get("Id")
                title = job.get("Title") or "Not Mentioned"
                location = job.get("PrimaryLocation") or "India"

                job_family = job.get("JobFamily")
                job_function = job.get("JobFunction")

                apply_link = (
                    "https://jpmc.fa.oraclecloud.com/hcmUI/"
                    "CandidateExperience/en/sites/CX_1001/job/"
                    + str(job_id)
                ) if job_id else ""

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)
                new_found += 1

                posted_at = (
                    job.get("PostedDate")
                    or job.get("PostingDate")
                    or job.get("CreationDate")
                )

                job_description = (
                    job.get("ExternalDescriptionStr")
                    or job.get("Description")
                    or job.get("JobDescription")
                    or ""
                )

                keywords = [
                    job_id,
                    job_family,
                    job_function,
                    posted_at
                ]

                keywords = [k for k in keywords if k]

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": list(set(keywords)),

                    "source": "JPMorgan Oracle Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title, job_family, job_function),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": job_function or job_family,
                    "salary": "Not disclosed",
                    "job_description": job_description,
                    "company_description": "JPMorgan Chase & Co. is a global financial services firm offering banking, markets, payments, technology and investment services.",
                    "posted_at": posted_at
                }

                jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            if new_found == 0:
                print("No new jobs found. Stopping.")
                break

            offset += PAGE_SIZE

            if offset > 2000:
                break

        conn.commit()

        print(f"\n✅ Saved {len(jobs)} JPMorgan jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return jobs


if __name__ == "__main__":

    jobs = scrape_jpmc_jobs()

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

    print("✅ Saved to", OUTPUT_FILE)