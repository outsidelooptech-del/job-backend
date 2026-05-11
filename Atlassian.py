import requests
import json
from database import get_connection
from save_job import save_job


COMPANY_NAME = "Atlassian"
COMPANY_LOGO = "https://img.logo.dev/atlassian.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

URL = "https://www.atlassian.com/endpoint/careers/listings"


def detect_work_mode(location, work_type):
    text = f"{location or ''} {work_type or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, employment_type):
    text = f"{title or ''} {employment_type or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return employment_type or "Full Time"


def detect_experience(title):
    if not title:
        return "Not specified"

    text = title.lower()

    if "intern" in text:
        return "Internship"

    if "graduate" in text or "fresher" in text or "entry level" in text:
        return "Freshers"

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "principal" in text or "staff" in text or "lead" in text or "manager" in text:
        return "5+ yrs"

    return "Not specified"


def fetch_atlassian_india_jobs():

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    print("Fetching Atlassian jobs...")

    try:
        response = requests.get(
            URL,
            headers=headers,
            timeout=30
        )
    except Exception as e:
        print("Request error:", e)
        return []

    if response.status_code != 200:
        print("Request failed:", response.status_code)
        return []

    try:
        data = response.json()
    except ValueError:
        print("Invalid JSON response")
        return []

    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    try:
        for job in data:

            locations = job.get("locations", [])

            if not any("India" in loc for loc in locations):
                continue

            title = (job.get("title") or "").strip()
            location = " | ".join(locations).strip()
            apply_link = (job.get("applyUrl") or "").strip()

            if not apply_link:
                continue

            if apply_link in seen_links:
                continue

            seen_links.add(apply_link)

            department = job.get("department")
            employment_type = job.get("employmentType")
            team = job.get("team")
            work_type = job.get("workType")

            keywords = []

            if department:
                keywords.append(department)

            if employment_type:
                keywords.append(employment_type)

            if team:
                keywords.append(team)

            if work_type:
                keywords.append(work_type)

            job_description = (
                job.get("description")
                or job.get("descriptionHtml")
                or ""
            )

            job_data = {
                "company": COMPANY_NAME,
                "title": title or "Not Mentioned",
                "location": location or "India",
                "apply_link": apply_link,
                "keywords": list(set(keywords)),

                "source": "Atlassian Careers API",
                "company_logo": COMPANY_LOGO,
                "work_mode": detect_work_mode(location, work_type),
                "job_type": detect_job_type(title, employment_type),
                "experience": detect_experience(title),
                "education": "Not specified",
                "department": department or team,
                "salary": "Not disclosed",
                "job_description": job_description,
                "company_description": "Atlassian is a global software company known for products like Jira, Confluence, Bitbucket and Trello.",
                "posted_at": job.get("postedDate") or job.get("updatedAt")
            }

            all_jobs.append(job_data)

            print("Saving:", title)

            save_job(job_data, cur)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Atlassian India jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs = fetch_atlassian_india_jobs()

    unique_jobs = {
        job["apply_link"]: job for job in jobs
    }

    final_jobs = list(unique_jobs.values())

    with open(
        "atlassian_india_jobs.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            final_jobs,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(f"\n✅ Scraped {len(final_jobs)} Atlassian India jobs!")
    print("Saved to atlassian_india_jobs.json")