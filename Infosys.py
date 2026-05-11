import requests
import json
import re

from save_job import save_job
from database import get_connection


COMPANY_NAME = "Infosys"
COMPANY_LOGO = "https://img.logo.dev/infosys.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

API_URL = "https://intapgateway.infosysapps.com/careersci/search/intapjbsrch/getCareerSearchJobs"
OUTPUT_FILE = "infosys_jobs.json"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://career.infosys.com/",
    "Origin": "https://career.infosys.com"
}

PARAMS = {
    "sourceId": ["1", "21"],
    "searchText": "ALL"
}


def clean_text(text):
    if not text:
        return ""

    text = str(text)

    replacements = {
        "â€¢": "•",
        "â€“": "-",
        "â€”": "-",
        "â€™": "'",
        "â€œ": '"',
        "â€�": '"'
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    return re.sub(r"\s+", " ", text).strip()


def detect_work_mode(location, description=""):
    text = f"{location or ''} {description or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, description=""):
    text = f"{title or ''} {description or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def normalize_experience(min_exp, max_exp, title=""):
    text = str(title or "").lower()

    if "intern" in text:
        return "Internship"

    if min_exp is not None and max_exp is not None:
        return f"{min_exp} - {max_exp} years"

    if min_exp is not None:
        return f"{min_exp}+ years"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "manager" in text or "lead" in text or "architect" in text:
        return "5+ yrs"

    return "Not specified"


def scrape_infosys_jobs():

    print("🚀 Fetching Infosys jobs...\n")

    conn = get_connection()
    cur = conn.cursor()

    all_jobs = []
    seen_links = set()

    try:
        response = requests.get(
            API_URL,
            params=PARAMS,
            headers=HEADERS,
            timeout=30
        )

        if response.status_code != 200:
            print("Request failed:", response.status_code)
            return []

        try:
            data = response.json()
        except ValueError:
            print("Invalid JSON response.")
            return []

        jobs = data if isinstance(data, list) else data.get("data", [])

        print("Total jobs from API:", len(jobs))

        for job in jobs[:500]:

            posting_id = job.get("postingId")
            reference_code = job.get("referenceCode")

            title = clean_text(job.get("postingTitle"))
            location = clean_text(job.get("location"))

            role_designation = clean_text(job.get("roleDesignation"))
            unit = clean_text(job.get("unit"))
            technical_requirement = clean_text(job.get("technicalRequirement"))
            roles_responsibilities = clean_text(job.get("rolesResponsibilities"))
            additional_responsibility = clean_text(job.get("additionalResponsibility"))

            min_exp = job.get("minExperienceLevel")
            max_exp = job.get("maxExperienceLevel")

            experience = normalize_experience(
                min_exp,
                max_exp,
                title
            )

            apply_link = (
                f"https://career.infosys.com/jobdesc?"
                f"jobReferenceCode={reference_code}&rc=0&jobType=normal"
                if reference_code else ""
            )

            if not apply_link:
                continue

            if apply_link in seen_links:
                continue

            seen_links.add(apply_link)

            job_description = " ".join(
                [
                    technical_requirement,
                    roles_responsibilities,
                    additional_responsibility
                ]
            ).strip()

            keywords = [
                posting_id,
                role_designation,
                unit,
                experience,
                technical_requirement,
                roles_responsibilities,
                additional_responsibility
            ]

            keywords = [k for k in keywords if k]

            job_data = {
                "company": COMPANY_NAME,
                "title": title or "Not Mentioned",
                "location": location or "India",
                "apply_link": apply_link,
                "keywords": list(set(keywords)),

                "source": "Infosys Careers API",
                "company_logo": COMPANY_LOGO,
                "work_mode": detect_work_mode(location, job_description),
                "job_type": detect_job_type(title, job_description),
                "experience": experience,
                "education": "Not specified",
                "department": unit or role_designation,
                "salary": "Not disclosed",
                "job_description": job_description,
                "company_description": "Infosys is a global IT services and consulting company providing digital, cloud, AI, engineering and business transformation services.",
                "posted_at": job.get("postedDate") or job.get("postingDate")
            }

            all_jobs.append(job_data)

            print("Saving:", title)

            save_job(job_data, cur)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Infosys jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs_data = scrape_infosys_jobs()

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