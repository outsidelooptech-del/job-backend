import requests
import re
import time
import json
from save_job import save_job
from database import get_connection


COMPANY_NAME = "Accenture"
COMPANY_LOGO = "https://img.logo.dev/accenture.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"  


def normalize_city(city):
    if not city:
        return None

    city_map = {
        "Bangalore": "Bengaluru",
        "Gurgaon": "Gurugram",
        "Bombay": "Mumbai"
    }

    return city_map.get(city, city)


def clean_experience(exp):
    if not exp:
        return None

    exp = str(exp)

    match = re.search(r'(\d+)\s*-\s*(\d+)', exp)
    if match:
        return f"{match.group(1)} - {match.group(2)} years"

    match = re.search(r'(\d+)\+?', exp)
    if match:
        return f"{match.group(1)}+ years"

    return exp


def detect_work_mode(location):
    if not location:
        return "Onsite"

    text = location.lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def fetch_accenture_jobs():
    url = "https://www.accenture.com/api/accenture/elastic/findjobs"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    start_index = 0
    page_size = 50
    max_limit = 1000

    all_jobs = []
    seen_ids = set()

    conn = get_connection()
    cur = conn.cursor()

    print("Started fetching Accenture jobs...")

    try:
        while True:
            if len(all_jobs) >= max_limit:
                print("Reached 1000 job limit. Stopping scraper.")
                break

            payload = {
                "startIndex": str(start_index),
                "maxResultSize": str(page_size),
                "jobKeyword": "",
                "jobCountry": "India",
                "jobLanguage": "en",
                "countrySite": "in-en",
                "sortBy": "1",
                "searchType": "vectorSearch",
                "enableQueryBoost": "true",
                "minScore": "0.6",
                "getFeedbackJudgmentEnabled": "true",
                "useCleanEmbedding": "true",
                "score": "true",
                "totalHits": "true",
                "debugQuery": "false",
                "jobFilters": []
            }

            try:
                print(f"Fetching jobs from index {start_index}...")
                response = requests.post(
                    url,
                    data=payload,
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
            except Exception:
                print("Invalid JSON response")
                break

            jobs = data.get("data", [])

            if not jobs:
                break

            for job in jobs:
                if len(all_jobs) >= max_limit:
                    break

                job_id = job.get("requisitionId") or job.get("guid")

                if not job_id or job_id in seen_ids:
                    continue

                seen_ids.add(job_id)

                title = job.get("title") or "Not Mentioned"

                city = normalize_city(job.get("feedCity"))
                region = job.get("regionName")
                country = job.get("country")

                location_parts = [city, region, country]
                full_location = ", ".join([part for part in location_parts if part]) or "Not Mentioned"

                raw_url = job.get("jobDetailUrl")
                apply_link = raw_url.replace("{0}", "in-en") if raw_url else "Not Mentioned"

                experience = clean_experience(job.get("yearsOfExperience"))
                department = job.get("businessArea")
                education = job.get("qualificationClean")
                career_level = job.get("careerLevel")

                keywords = []

                fields_to_collect = [
                    career_level,
                    department,
                    education,
                    experience
                ]

                skills_raw = job.get("skills")

                if isinstance(skills_raw, list):
                    fields_to_collect.extend(skills_raw)
                elif skills_raw:
                    fields_to_collect.append(skills_raw)

                for field in fields_to_collect:
                    if field and field != "Not Mentioned":
                        keywords.append(str(field).strip())

                keywords = list(set(keywords))

                job_description = (
                    job.get("jobDescription")
                    or job.get("description")
                    or job.get("shortDescription")
                    or ""
                )

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": full_location,
                    "apply_link": apply_link,
                    "keywords": keywords,

                    "source": "Accenture API",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(full_location),
                    "job_type": "Full Time",
                    "experience": experience,
                    "education": education or "Not specified",
                    "department": department,
                    "salary": "Not disclosed",
                    "job_description": job_description,
                    "company_description": "Accenture is a global professional services company with capabilities in digital, cloud and security.",
                    "posted_at": None
                }

                all_jobs.append(job_data)

                print("Saving:", title)
                save_job(job_data, cur)

            if len(jobs) < page_size:
                break

            start_index += page_size
            time.sleep(1)

        conn.commit()
        print("Finished saving Accenture jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":
    jobs = fetch_accenture_jobs()

    print(f"Total Jobs Collected: {len(jobs)}")

    with open("accenture_india_jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)

    print("Saved to accenture_india_jobs.json")