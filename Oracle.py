import requests
import json
import time

from save_job import save_job
from database import get_connection


# ==============================
# CONFIG
# ==============================

COMPANY_NAME = "Oracle"
COMPANY_LOGO = "https://img.logo.dev/oracle.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://eeho.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
OUTPUT_FILE = "oracle_india_jobs.json"

HEADERS = {
    "accept": "*/*",
    "accept-language": "en",
    "content-type": "application/vnd.oracle.adf.resourceitem+json;charset=utf-8",
    "origin": "https://careers.oracle.com",
    "referer": "https://careers.oracle.com/",
    "user-agent": "Mozilla/5.0",
    "ora-irc-language": "en",
    "ora-irc-cx-userid": "1e3064ac-f55d-49f3-8717-d890a0337937"
}

SITE_NUMBER = "CX_45001"
LOCATION_ID = "300000000106947"

LIMIT = 50
MAX_JOBS = 500


# ==============================
# HELPERS
# ==============================

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


def detect_experience(title):
    text = (title or "").lower()

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

    return "Not specified"


# ==============================
# SCRAPER
# ==============================

def scrape_oracle_jobs():

    all_jobs = []
    seen_links = set()
    offset = 0

    print("🚀 Fetching Oracle India jobs...\n")

    conn = get_connection()
    cur = conn.cursor()

    try:
        while len(all_jobs) < MAX_JOBS:

            finder = (
                "findReqs;"
                f"siteNumber={SITE_NUMBER},"
                "facetsList=LOCATIONS%3BWORK_LOCATIONS%3BWORKPLACE_TYPES%3B"
                "TITLES%3BCATEGORIES%3BORGANIZATIONS%3BPOSTING_DATES%3BFLEX_FIELDS,"
                f"limit={LIMIT},"
                f"locationId={LOCATION_ID},"
                f"offset={offset},"
                "sortBy=POSTING_DATES_DESC"
            )

            params = {
                "onlyData": "true",
                "expand": (
                    "requisitionList.workLocation,"
                    "requisitionList.otherWorkLocations,"
                    "requisitionList.secondaryLocations,"
                    "flexFieldsFacet.values,"
                    "requisitionList.requisitionFlexFields"
                ),
                "finder": finder
            }

            try:
                response = requests.get(
                    BASE_URL,
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

                if len(all_jobs) >= MAX_JOBS:
                    break

                job_id = job.get("Id")
                title = job.get("Title") or "Not Mentioned"
                location = job.get("PrimaryLocation") or "India"
                posted_date = job.get("PostedDate")

                apply_link = (
                    f"https://careers.oracle.com/jobs/#en/sites/jobsearch/job/{job_id}"
                    if job_id else ""
                )

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)
                new_found += 1

                job_family = (
                    job.get("JobFamily")
                    or job.get("JobFunction")
                    or job.get("Category")
                )

                job_description = (
                    job.get("ExternalDescriptionStr")
                    or job.get("Description")
                    or job.get("JobDescription")
                    or ""
                )

                keywords = [
                    job_id,
                    posted_date,
                    job_family
                ]

                keywords = [str(k) for k in keywords if k]

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": list(set(keywords)),

                    "source": "Oracle Careers API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": job_family,
                    "salary": "Not disclosed",
                    "job_description": job_description,
                    "company_description": "Oracle is a global technology company known for cloud infrastructure, database software, enterprise applications, AI and business platforms.",
                    "posted_at": posted_date
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            print(f"Collected {len(all_jobs)} jobs...")

            if new_found == 0:
                print("No new jobs found. Stopping.")
                break

            offset += LIMIT

            time.sleep(1)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Oracle jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


# ==============================
# MAIN
# ==============================

if __name__ == "__main__":

    jobs = scrape_oracle_jobs()

    print(f"\n✅ Total jobs collected: {len(jobs)}")

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

    print("📂 Saved to", OUTPUT_FILE)