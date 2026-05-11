from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

import json
import time

from save_job import save_job
from database import get_connection


BASE_URL = "https://jobs.dell.com/en/search-jobs/India/375/2/1269750/22/79/50/2"
COMPANY_NAME = "Dell"
COMPANY_LOGO = "https://img.logo.dev/dell.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

OUTPUT_FILE = "Dell_India_jobs.json"


def detect_work_mode(location):
    text = (location or "").lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, category):
    text = f"{title or ''} {category or ''}".lower()

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

    if "graduate" in text or "fresher" in text or "entry level" in text:
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
    ):
        return "5+ yrs"

    return "Not specified"


def scrape_dell_jobs():

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    conn = get_connection()
    cur = conn.cursor()

    all_jobs = []
    seen_links = set()

    page = 1
    max_pages = 12

    print("🚀 Dell Job Scraper Started...")

    try:
        while page <= max_pages:

            url = f"{BASE_URL}?p={page}"

            print(f"\nScraping Dell jobs — page {page}")
            driver.get(url)

            time.sleep(3)

            job_cards = driver.find_elements(
                By.CSS_SELECTOR,
                "li a[data-job-id]"
            )

            if not job_cards:
                print("No more Dell jobs found.")
                break

            jobs_found = 0

            for card in job_cards:

                try:
                    job_url = card.get_attribute("href")

                    if not job_url:
                        continue

                    if job_url in seen_links:
                        continue

                    seen_links.add(job_url)

                    title = card.find_element(
                        By.TAG_NAME,
                        "h2"
                    ).text.strip()

                    category = None

                    try:
                        category = card.find_element(
                            By.CSS_SELECTOR,
                            ".job-category"
                        ).text.strip()
                    except Exception:
                        category = None

                    location = None

                    try:
                        location = card.find_element(
                            By.CSS_SELECTOR,
                            ".job-location"
                        ).text.strip()
                    except Exception:
                        location = None

                    keywords = list(set([
                        k for k in [category] if k
                    ]))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title or "Not Mentioned",
                        "location": location or "India",
                        "apply_link": job_url,
                        "keywords": keywords,

                        "source": "Dell Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location),
                        "job_type": detect_job_type(title, category),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": category,
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "Dell Technologies is a global technology company providing computers, servers, storage, cloud, cybersecurity and enterprise solutions.",
                        "posted_at": None
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                    jobs_found += 1

                except Exception as e:
                    print("Skipping card:", e)

            if jobs_found == 0:
                print("No jobs parsed — stopping.")
                break

            page += 1
            time.sleep(1)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Dell jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        driver.quit()
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs = scrape_dell_jobs()

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

    print(f"\n✅ Scraped {len(jobs)} Dell jobs!")