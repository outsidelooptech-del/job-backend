import requests
from bs4 import BeautifulSoup
import json
import time
from database import get_connection
from save_job import save_job


COMPANY_NAME = "Apple"

BASE_URL = "https://jobs.apple.com"

SEARCH_URL = (
    "https://jobs.apple.com/en-in/search"
    "?location=india-INDC&page={}"
)

LOGO_URL = (
    "https://img.logo.dev/apple.com"
    "?token=pk_ak69YmTsSK6Yhcs1Its-RA"
)


def detect_work_mode(location):
    if not location:
        return "Onsite"

    text = location.lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title):
    if not title:
        return "Full Time"

    text = title.lower()

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def detect_experience(title):
    if not title:
        return "Not specified"

    text = title.lower()

    if "intern" in text:
        return "Internship"

    if (
        "graduate" in text
        or "student" in text
        or "fresher" in text
        or "university" in text
    ):
        return "Freshers"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if (
        "lead" in text
        or "manager" in text
        or "principal" in text
        or "staff" in text
    ):
        return "5+ yrs"

    return "0-2 yrs"


def fetch_apple_india_jobs():

    headers = {
        "User-Agent": "Mozilla/5.0",
    }

    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    try:

        page = 1

        while True:

            print(f"\nScraping {COMPANY_NAME} India jobs — page {page}")

            try:
                r = requests.get(
                    SEARCH_URL.format(page),
                    headers=headers,
                    timeout=30
                )

            except Exception as e:
                print("Request error:", e)
                break

            if r.status_code != 200:
                print("Request failed:", r.status_code)
                break

            soup = BeautifulSoup(r.text, "html.parser")

            job_cards = soup.select("a.link-inline")

            if not job_cards:
                print("No more jobs found. Stopping.")
                break

            page_jobs = 0

            for job in job_cards:

                title = job.get_text(strip=True)
                href = job.get("href")

                if not href:
                    continue

                apply_link = BASE_URL + href

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)

                parent = job.find_parent("div", class_="job-title")

                location = ""
                posted_at = None
                department = None

                keywords = []

                if parent:

                    try:
                        loc_tag = parent.select_one(
                            ".job-title-location span:last-child"
                        )

                        if loc_tag:
                            location = loc_tag.get_text(strip=True)

                    except Exception:
                        pass

                    try:
                        date_tag = parent.select_one(
                            ".job-posted-date"
                        )

                        if date_tag:
                            posted_at = date_tag.get_text(strip=True)
                            keywords.append(posted_at)

                    except Exception:
                        pass

                    try:
                        dept_tag = parent.select_one(
                            ".team-name"
                        )

                        if dept_tag:
                            department = dept_tag.get_text(strip=True)
                            keywords.append(department)

                    except Exception:
                        pass

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title or "Not Mentioned",
                    "location": location or "India",
                    "apply_link": apply_link,
                    "keywords": list(set([k for k in keywords if k])),

                    # EXTRA FIELDS
                    "source": "Apple Careers",
                    "company_logo": LOGO_URL,
                    "work_mode": detect_work_mode(location),
                    "job_type": detect_job_type(title),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": department,
                    "salary": "Not disclosed",
                    "posted_at": posted_at,

                    "company_description": (
                        "Apple is a global technology company "
                        "known for iPhone, Mac, iPad, AI, and "
                        "software innovation."
                    ),

                    "job_description": ""
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

                page_jobs += 1

            if page_jobs == 0:
                break

            page += 1

            time.sleep(1)

        conn.commit()

    except Exception as e:

        conn.rollback()

        print("Fatal error:", e)

    finally:

        cur.close()
        conn.close()

    return all_jobs


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    jobs = fetch_apple_india_jobs()

    with open(
        "apple_india_jobs.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            jobs,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(f"\n✅ Scraped {len(jobs)} Apple India jobs!")
    print("Saved to apple_india_jobs.json")