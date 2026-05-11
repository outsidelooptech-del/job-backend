import requests
from bs4 import BeautifulSoup
import json
import time

from save_job import save_job
from database import get_connection


# ----------------------------
# CONFIG
# ----------------------------

COMPANY_NAME = "Mahindra"
COMPANY_LOGO = "https://img.logo.dev/mahindra.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://jobs.mahindracareers.com/search/"
OUTPUT_FILE = "mahindra_jobs.json"

PAGE_SIZE = 10
MAX_PAGES = 20

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def detect_work_mode(location, title=""):
    text = f"{location or ''} {title or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, business=""):
    text = f"{title or ''} {business or ''}".lower()

    if "intern" in text or "trainee" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def detect_experience(title):
    text = (title or "").lower()

    if "intern" in text or "trainee" in text:
        return "Internship"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "manager" in text or "lead" in text or "head" in text:
        return "5+ yrs"

    return "Not specified"


def scrape_mahindra_jobs():

    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    print("🚀 Fetching Mahindra Careers jobs...\n")

    try:

        for page in range(MAX_PAGES):

            startrow = page * PAGE_SIZE

            params = {
                "q": "",
                "sortColumn": "referencedate",
                "sortDirection": "desc",
                "startrow": startrow
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
                print("Failed at page", page + 1)
                break

            soup = BeautifulSoup(response.text, "html.parser")

            rows = soup.find_all("tr", class_="data-row")

            if not rows:
                print("No more jobs found.")
                break

            jobs_found = 0

            for row in rows:

                title_tag = row.find("a", class_="jobTitle-link")
                location_tag = row.find("span", class_="jobLocation")
                facility_tag = row.find("span", class_="jobFacility")
                business_tag = row.find("span", class_="jobShifttype")

                title = title_tag.text.strip() if title_tag else ""
                location = location_tag.text.strip() if location_tag else "India"
                function = facility_tag.text.strip() if facility_tag else None
                business = business_tag.text.strip() if business_tag else None

                apply_link = (
                    "https://jobs.mahindracareers.com" + title_tag["href"]
                    if title_tag and title_tag.get("href")
                    else ""
                )

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)

                keywords = [
                    function,
                    business
                ]

                keywords = [k for k in keywords if k]

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title or "Not Mentioned",
                    "location": location or "India",
                    "apply_link": apply_link,
                    "keywords": list(set(keywords)),

                    "source": "Mahindra Careers",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title, business),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": function or business,
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "Mahindra is an Indian multinational group operating across automotive, farm equipment, technology, financial services and industrial sectors.",
                    "posted_at": None
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

                jobs_found += 1

            if jobs_found == 0:
                print("No jobs parsed. Stopping.")
                break

            print(f"Page {page + 1} scraped. Total jobs: {len(all_jobs)}")

            time.sleep(0.5)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Mahindra jobs to database.")

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

    jobs_data = scrape_mahindra_jobs()

    print(f"\n✅ Total jobs collected: {len(jobs_data)}")

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