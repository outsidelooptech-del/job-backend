import requests
import json
from save_job import save_job
from database import get_connection


COMPANY_NAME = "Goldman Sachs"
COMPANY_LOGO = "https://img.logo.dev/goldmansachs.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

URL = "https://api-higher.gs.com/gateway/api/v1/graphql"
OUTPUT_FILE = "goldman_sachs_jobs.json"

HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://higher.gs.com",
    "Referer": "https://higher.gs.com/",
    "User-Agent": "Mozilla/5.0"
}

QUERY = """
query GetRoles($searchQueryInput: RoleSearchQueryInput!) {
  roleSearch(searchQueryInput: $searchQueryInput) {
    totalCount
    items {
      roleId
      corporateTitle
      jobTitle
      jobFunction
      division
      locations {
        primary
        state
        country
        city
      }
      externalSource {
        sourceId
      }
    }
  }
}
"""


def detect_work_mode(location, title=""):
    text = f"{location or ''} {title or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, corporate_title=""):
    text = f"{title or ''} {corporate_title or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def detect_experience(title, corporate_title=""):
    text = f"{title or ''} {corporate_title or ''}".lower()

    if "intern" in text or "summer analyst" in text:
        return "Internship"

    if (
        "analyst" in text
        or "associate" in text
        or "early career" in text
    ):
        return "0-2 yrs"

    if "vice president" in text or "vp" in text:
        return "5+ yrs"

    if (
        "manager" in text
        or "lead" in text
        or "director" in text
        or "executive director" in text
    ):
        return "7+ yrs"

    return "Not specified"


def scrape_goldman_jobs():

    all_jobs = []
    seen_links = set()

    page_number = 0
    page_size = 20
    max_jobs = 500

    conn = get_connection()
    cur = conn.cursor()

    print("\n🚀 Goldman Sachs Job Scraper Started...\n")

    try:
        while len(all_jobs) < max_jobs:

            print(f"Fetching Page {page_number + 1}")

            payload = {
                "operationName": "GetRoles",
                "query": QUERY,
                "variables": {
                    "searchQueryInput": {
                        "page": {
                            "pageSize": page_size,
                            "pageNumber": page_number
                        },
                        "sort": {
                            "sortStrategy": "RELEVANCE",
                            "sortOrder": "DESC"
                        },
                        "experiences": [
                            "EARLY_CAREER",
                            "PROFESSIONAL"
                        ],
                        "filters": [
                            {
                                "filterCategoryType": "LOCATION",
                                "filters": [
                                    {
                                        "filter": "India"
                                    }
                                ]
                            }
                        ],
                        "searchTerm": ""
                    }
                }
            }

            try:
                response = requests.post(
                    URL,
                    headers=HEADERS,
                    json=payload,
                    timeout=30
                )
            except Exception as e:
                print("Request error:", e)
                break

            if response.status_code != 200:
                print("Failed:", response.status_code)
                break

            try:
                data = response.json()
            except ValueError:
                print("Invalid JSON response.")
                break

            roles = (
                data.get("data", {})
                .get("roleSearch", {})
                .get("items", [])
            )

            if not roles:
                break

            new_found = 0

            for role in roles:

                if len(all_jobs) >= max_jobs:
                    break

                locations = role.get("locations", [])
                city = state = country = ""

                if locations:
                    loc = locations[0]
                    city = loc.get("city", "")
                    state = loc.get("state", "")
                    country = loc.get("country", "")

                location_text = ", ".join(
                    [x for x in [city, state, country] if x]
                )

                source_id = (
                    role.get("externalSource", {})
                    .get("sourceId", "")
                )

                job_url = (
                    f"https://higher.gs.com/roles/{source_id}"
                    if source_id else ""
                )

                if not job_url:
                    continue

                if job_url in seen_links:
                    continue

                seen_links.add(job_url)
                new_found += 1

                title = role.get("jobTitle") or "Not Mentioned"
                corporate_title = role.get("corporateTitle")
                job_function = role.get("jobFunction")
                division = role.get("division")

                keywords = [
                    role.get("roleId"),
                    corporate_title,
                    job_function,
                    division
                ]

                keywords = [k for k in keywords if k]

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location_text or "India",
                    "apply_link": job_url,
                    "keywords": list(set(keywords)),

                    "source": "Goldman Sachs Higher API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location_text, title),
                    "job_type": detect_job_type(title, corporate_title),
                    "experience": detect_experience(title, corporate_title),
                    "education": "Not specified",
                    "department": division or job_function,
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "Goldman Sachs is a global investment banking, securities and investment management firm.",
                    "posted_at": None
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            if new_found == 0:
                break

            page_number += 1

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Goldman Sachs jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs_data = scrape_goldman_jobs()

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