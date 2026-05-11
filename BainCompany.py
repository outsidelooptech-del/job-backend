import requests
import json
import time
from save_job import save_job
from database import get_connection


# ===============================
# CONFIG
# ===============================

COMPANY_NAME = "Bain & Company"
BASE_URL = "https://www.bain.com"
API_URL = "https://www.bain.com/en/api/jobsearch/keyword/get"
OUTPUT_FILE = "bain_india_jobs.json"

session = requests.Session()

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.bain.com/careers/find-a-role/",
    "Origin": "https://www.bain.com"
}

session.headers.update(headers)

# Warm session
try:
    session.get("https://www.bain.com/careers/find-a-role/", timeout=30)
except Exception:
    pass


# ===============================
# LOCATION NORMALIZER
# ===============================

INDIAN_CITIES = [
    "bengaluru", "bangalore",
    "mumbai", "chennai",
    "hyderabad", "kolkata",
    "pune", "delhi", "gurgaon",
    "noida", "india"
]


def normalize_location(location_list):

    if not location_list:
        return "India"

    joined = ", ".join(location_list).lower()

    for city in INDIAN_CITIES:
        if city in joined:
            if city in ["bangalore", "bengaluru"]:
                return "Bengaluru"
            if city == "gurgaon":
                return "Gurugram"

            return city.capitalize()

    return "India"


# ===============================
# SCRAPER
# ===============================

def fetch_bain_india_jobs():

    all_jobs = []
    seen_links = set()
    page = 0

    print(f"🚀 Scraping {COMPANY_NAME} India jobs...")

    # ✅ Database connection once
    conn = get_connection()
    cur = conn.cursor()

    try:

        while True:

            print(f"\nScraping page {page}")

            params = {
                "start": page,
                "results": 10,
                "filters": "offices(274,276,275)|",
                "searchValue": ""
            }

            try:
                response = session.get(API_URL, params=params, timeout=30)
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

            jobs = data.get("results", [])

            if not jobs:
                break

            for job in jobs:

                title = job.get("JobTitle", "").strip()

                locations_raw = job.get("Location", [])
                location = normalize_location(locations_raw)

                link_part = job.get("Link", "").strip()
                if not link_part:
                    continue

                apply_link = BASE_URL + link_part

                if apply_link in seen_links:
                    continue
                seen_links.add(apply_link)

                keywords = list(set([
                    job.get("Category"),
                    job.get("JobType"),
                    job.get("PostingDate"),
                    job.get("ReqId")
                ]))

                keywords = [k for k in keywords if k]

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title or "Not Mentioned",
                    "location": location or "India",
                    "apply_link": apply_link,
                    "keywords": keywords
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            page += 1
            time.sleep(1)

    finally:
        conn.commit()
        cur.close()
        conn.close()

    return all_jobs


# ===============================
# RUN
# ===============================

if __name__ == "__main__":

    jobs = fetch_bain_india_jobs()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Scraped {len(jobs)} {COMPANY_NAME} India jobs!")
    print("Saved to", OUTPUT_FILE)