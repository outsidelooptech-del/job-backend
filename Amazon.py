import requests
import json
import time
from database import get_connection
from save_job import save_job


COMPANY_NAME = "Amazon"
COMPANY_DOMAIN = "amazon.com"

API_URL = "https://www.amazon.jobs/api/jobs/search?is_als=true"

# ✅ HARD LIMIT
MAX_JOBS = 700


def fetch_amazon_india_jobs():

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    # ✅ Database connection once
    conn = get_connection()
    cur = conn.cursor()

    all_jobs = []
    seen_links = set()

    start = 0
    size = 10

    try:

        while True:

            # ✅ Stop if global limit reached
            if len(all_jobs) >= MAX_JOBS:
                print("✅ Reached 700 job limit. Stopping scraper.")
                break

            print(f"\nScraping {COMPANY_NAME} India jobs — offset {start}")

            payload = {
                "accessLevel": "EXTERNAL",
                "locationFacets": [
                    [
                        {
                            "name": "country",
                            "requestedFacetCount": 9999,
                            "values": [{"name": "IN"}]
                        }
                    ]
                ],
                "query": "",
                "size": size,
                "start": start,
                "sort": {
                    "sortOrder": "DESCENDING",
                    "sortType": "SCORE"
                }
            }

            try:
                response = requests.post(
                    API_URL,
                    json=payload,
                    headers=headers,
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
                print("Invalid JSON response")
                break

            hits = data.get("searchHits", [])

            if not hits:
                print("No more jobs found.")
                break

            new_found = 0

            for job in hits:

                # ✅ Stop if limit reached
                if len(all_jobs) >= MAX_JOBS:
                    break

                fields = job.get("fields", {})

                title = fields.get("title", ["Not Mentioned"])[0].strip()

                location = fields.get(
                    "normalizedLocation",
                    ["India"]
                )[0].strip()

                job_id = fields.get(
                    "icimsJobId",
                    [""]
                )[0].strip()

                apply_link = (
                    f"https://www.amazon.jobs/en/jobs/{job_id}"
                    if job_id else ""
                )

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)
                new_found += 1

                # =========================
                # EXTRA DATA
                # =========================

                department = None
                experience = None
                education = None
                salary = "Not disclosed"
                job_type = "Full Time"
                work_mode = None
                posted_at = None

                keywords = []

                # Posted date
                if fields.get("postedDate"):
                    posted_at = fields["postedDate"][0]
                    keywords.append(posted_at)

                # Department / Job Family
                if fields.get("jobFamily"):
                    department = fields["jobFamily"][0]
                    keywords.append(department)

                # Employment Type
                if fields.get("employmentType"):
                    job_type = fields["employmentType"][0]
                    keywords.append(job_type)

                # Business Category
                if fields.get("businessCategory"):
                    keywords.append(fields["businessCategory"][0])

                # Basic Experience Extraction
                title_lower = title.lower()

                if "intern" in title_lower:
                    experience = "Internship"
                elif "senior" in title_lower or "sr." in title_lower:
                    experience = "Senior Level"
                elif "manager" in title_lower:
                    experience = "Manager Level"
                elif "principal" in title_lower:
                    experience = "Principal Level"
                else:
                    experience = "Not specified"

                # Work mode detection
                location_lower = location.lower()

                if "remote" in location_lower:
                    work_mode = "Remote"
                elif "hybrid" in location_lower:
                    work_mode = "Hybrid"
                else:
                    work_mode = "Onsite"

                # Logo.dev
                company_logo = f"https://img.logo.dev/{COMPANY_DOMAIN}?token=pk_ak69YmTsSK6Yhcs1Its-RA"

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,

                    # ✅ NEW FIELDS
                    "company_logo": company_logo,
                    "job_type": job_type,
                    "work_mode": work_mode,
                    "department": department,
                    "experience": experience,
                    "education": education,
                    "salary": salary,
                    "posted_at": posted_at,

                    "keywords": list(set([
                        k for k in keywords if k
                    ]))
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            if new_found == 0:
                break

            start += size
            time.sleep(1)

        conn.commit()

    finally:
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs = fetch_amazon_india_jobs()

    with open(
        "amazon_india_jobs.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            jobs,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"\n✅ Total {COMPANY_NAME} India jobs scraped: {len(jobs)}"
    )