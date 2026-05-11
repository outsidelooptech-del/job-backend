import json
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from save_job import save_job
from database import get_connection


# =============================
# CONFIG
# =============================

COMPANY_NAME = "Philips"
COMPANY_LOGO = "https://img.logo.dev/philips.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://www.careers.philips.com/in/en/search-results?keywords=&from={}&s=1"
OUTPUT_FILE = "philips_india_jobs.json"

MAX_JOBS = 500
OFFSET_STEP = 10


# =============================
# HELPERS
# =============================

def detect_work_mode(location, title=""):
    text = f"{location or ''} {title or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, job_type_text=""):
    text = f"{title or ''} {job_type_text or ''}".lower()

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

    if "fresher" in text or "graduate" in text or "entry level" in text:
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
        or "staff" in text
    ):
        return "5+ yrs"

    return "Not specified"


# =============================
# SCRAPER
# =============================

def scrape_philips_jobs():

    conn = get_connection()
    cur = conn.cursor()

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    jobs_collected = []
    seen_links = set()

    offset = 0

    print("🚀 Scraping Philips India jobs...\n")

    try:
        while len(jobs_collected) < MAX_JOBS:

            url = BASE_URL.format(offset)

            print(f"\nFetching offset: {offset}")

            driver.get(url)

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "li.jobs-list-item")
                    )
                )
            except Exception:
                print("No jobs found. Ending pagination.")
                break

            time.sleep(2)

            jobs = driver.find_elements(By.CSS_SELECTOR, "li.jobs-list-item")

            if not jobs:
                print("No job cards found.")
                break

            for job in jobs:

                if len(jobs_collected) >= MAX_JOBS:
                    break

                try:
                    title = job.find_element(
                        By.CSS_SELECTOR,
                        ".job-title span"
                    ).text.strip() or "Not Mentioned"

                    apply_link = job.find_element(
                        By.CSS_SELECTOR,
                        "a[data-ph-at-id='job-link']"
                    ).get_attribute("href") or ""

                    if not apply_link:
                        continue

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    location = job.find_element(
                        By.CSS_SELECTOR,
                        ".job-location"
                    ).text.strip() or "India"

                    category = job.find_element(
                        By.CSS_SELECTOR,
                        ".category"
                    ).text.strip()

                    job_type_text = job.find_element(
                        By.CSS_SELECTOR,
                        ".type"
                    ).text.strip()

                    try:
                        posted_date = job.find_element(
                            By.CSS_SELECTOR,
                            ".job-postdate"
                        ).text.strip()
                    except Exception:
                        posted_date = None

                    keywords = list(set([
                        k for k in [
                            category,
                            job_type_text,
                            posted_date,
                            location
                        ]
                        if k
                    ]))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title,
                        "location": location,
                        "apply_link": apply_link,
                        "keywords": keywords,

                        "source": "Philips Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location, title),
                        "job_type": detect_job_type(title, job_type_text),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": category or "Not specified",
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "Philips is a global health technology company focused on healthcare innovation, medical devices, diagnostics, and personal health solutions.",
                        "posted_at": posted_date
                    }

                    jobs_collected.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping job due to error:", e)
                    continue

            print("Collected so far:", len(jobs_collected))

            offset += OFFSET_STEP
            time.sleep(1)

        conn.commit()

        print(f"\n✅ Saved {len(jobs_collected)} Philips jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()
        driver.quit()

    return jobs_collected


# =============================
# MAIN
# =============================

if __name__ == "__main__":

    jobs_data = scrape_philips_jobs()

    print(f"\n✅ Total Jobs Collected: {len(jobs_data)}")

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