import requests
import json
from bs4 import BeautifulSoup

from save_job import save_job
from database import get_connection


COMPANY_NAME = "DXC Technology"
COMPANY_LOGO = "https://img.logo.dev/dxc.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://jobsapi-internal.m-cloud.io/api/job"
OUTPUT_FILE = "dxc_india_jobs.json"


def fetch_jobs(limit=10, offset=1):

    params = {
        "callback": "CWS.jobs.jobCallback",
        "facet[]": [
            "compliment:India",
            "is_internal:DXCJobs"
        ],
        "sortfield": "open_date",
        "sortorder": "descending",
        "Limit": limit,
        "Organization": 2492,
        "offset": offset,
        "fuzzy": "false",
        "facetlist[]": [
            "compliment",
            "store_id",
            "primary_city",
            "primary_category",
            "employment_type"
        ]
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://careers.dxc.com/job-search-results/?compliment[]=India"
    }

    response = requests.get(
        BASE_URL,
        params=params,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    text = response.text.strip()

    if text.startswith("CWS.jobs.jobCallback"):
        text = text[text.find("(") + 1:-1]

    data = json.loads(text)

    return data.get("queryResult", [])


def clean_description(html_text):

    if not html_text:
        return ""

    soup = BeautifulSoup(html_text, "html.parser")

    return soup.get_text(separator=" ", strip=True)


def detect_work_mode(description="", location=""):

    text = f"{description} {location}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_experience(title="", description=""):

    text = f"{title} {description}".lower()

    if "intern" in text:
        return "Internship"

    if "fresher" in text:
        return "Freshers"

    if "entry level" in text:
        return "Entry Level"

    if "senior" in text or "lead" in text or "manager" in text:
        return "5+ yrs"

    if "associate" in text or "analyst" in text:
        return "0-2 yrs"

    return "Not specified"


def detect_job_type(employment_type=""):

    text = employment_type.lower()

    if "part" in text:
        return "Part Time"

    if "contract" in text:
        return "Contract"

    if "intern" in text:
        return "Internship"

    return "Full Time"


def scrape_all_jobs(max_pages=50, limit=10):

    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    print(f"\n🚀 Starting {COMPANY_NAME} India Job Scraper...\n")

    try:

        for page in range(1, max_pages + 1):

            offset = 1 + (page - 1) * limit

            print(f"\n📌 Fetching Page {page} | Offset={offset}")

            try:
                jobs = fetch_jobs(limit=limit, offset=offset)
            except Exception as e:
                print("Request failed:", e)
                break

            if not jobs:
                print("No more jobs found.")
                break

            jobs_found = 0

            for job in jobs:

                try:

                    city = job.get("primary_city", "")
                    state = job.get("primary_state", "")
                    country = job.get("primary_country", "")

                    location = ", ".join(
                        [x for x in [city, state, country] if x]
                    )

                    description_text = clean_description(
                        job.get("description")
                    )

                    apply_link = job.get("seo_url", "").strip()

                    if not apply_link:
                        continue

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    employment_type = job.get("employment_type", "")
                    category = job.get("primary_category", "")

                    keywords = list(set([
                        job.get("id"),
                        category,
                        employment_type,
                        city,
                        state,
                        country
                    ]))

                    keywords = [k for k in keywords if k]

                    title = job.get("title", "").strip()

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title or "Not Mentioned",
                        "location": location or "India",
                        "apply_link": apply_link,
                        "keywords": keywords,

                        "source": "DXC Careers API",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(
                            description_text,
                            location
                        ),
                        "job_type": detect_job_type(employment_type),
                        "experience": detect_experience(
                            title,
                            description_text
                        ),
                        "education": "Not specified",
                        "department": category or None,
                        "salary": "Not disclosed",
                        "job_description": description_text,
                        "company_description": "DXC Technology is a global IT services and consulting company.",
                        "posted_at": job.get("open_date")
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                    jobs_found += 1

                except Exception as e:
                    print("Skipping job:", e)

            if jobs_found == 0:
                print("No jobs parsed. Stopping.")
                break

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal Error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs_data = scrape_all_jobs(
        max_pages=100,
        limit=10
    )

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