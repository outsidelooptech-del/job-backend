import json
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from save_job import save_job
from database import get_connection


# =============================
# CONFIG
# =============================

COMPANY_NAME = "Synopsys"
COMPANY_LOGO = "https://img.logo.dev/synopsys.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

START_URL = "https://careers.synopsys.com/search-jobs/India/44408/2/1269750/22/79/50/2"
OUTPUT_FILE = "synopsys_india_jobs.json"

MAX_JOBS = 500


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


def detect_job_type(title):
    text = (title or "").lower()

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
# DRIVER SETUP
# =============================

def setup_driver():

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    return driver


# =============================
# SCRAPER
# =============================

def scrape_synopsys_jobs():

    conn = get_connection()
    cur = conn.cursor()

    driver = setup_driver()
    wait = WebDriverWait(driver, 20)

    all_jobs = []
    seen_job_ids = set()
    seen_links = set()

    page_number = 1

    print("🚀 Scraping Synopsys India jobs...\n")

    try:
        driver.get(START_URL)

        while len(all_jobs) < MAX_JOBS:

            print(f"\nScraping Page {page_number}")

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "li.search-results-list__list-item")
                    )
                )
            except Exception:
                print("No jobs found.")
                break

            time.sleep(2)

            jobs = driver.find_elements(
                By.CSS_SELECTOR,
                "li.search-results-list__list-item"
            )

            print("Jobs found:", len(jobs))

            if not jobs:
                break

            try:
                first_job_before = jobs[0].find_element(
                    By.CSS_SELECTOR,
                    "span.jobId"
                ).text
            except Exception:
                first_job_before = ""

            for job in jobs:

                if len(all_jobs) >= MAX_JOBS:
                    break

                try:
                    job_id = job.find_element(
                        By.CSS_SELECTOR,
                        "span.jobId"
                    ).text.replace("Job ID:", "").strip()
                except Exception:
                    continue

                try:
                    title = job.find_element(
                        By.CSS_SELECTOR,
                        "a.sr-job-link h2"
                    ).text.strip() or "Not Mentioned"
                except Exception:
                    title = "Not Mentioned"

                try:
                    apply_link = job.find_element(
                        By.CSS_SELECTOR,
                        "a.sr-job-link"
                    ).get_attribute("href") or ""
                except Exception:
                    apply_link = ""

                if not apply_link:
                    continue

                if job_id in seen_job_ids or apply_link in seen_links:
                    continue

                seen_job_ids.add(job_id)
                seen_links.add(apply_link)

                try:
                    location = job.find_element(
                        By.CSS_SELECTOR,
                        "span.job-location"
                    ).text.strip()
                except Exception:
                    location = "India"

                try:
                    category = job.find_element(
                        By.CSS_SELECTOR,
                        "span.category"
                    ).text.replace("Category:", "").strip()
                except Exception:
                    category = None

                try:
                    posted_date = job.find_element(
                        By.CSS_SELECTOR,
                        "span.job-date-posted"
                    ).text.replace("Posted:", "").strip()
                except Exception:
                    posted_date = None

                keywords = list(set([
                    str(k)
                    for k in [
                        job_id,
                        category,
                        posted_date,
                        location,
                        f"Page {page_number}"
                    ]
                    if k
                ]))

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": keywords,

                    "source": "Synopsys Careers",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": category or "Not specified",
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "Synopsys is a global electronic design automation company providing software, IP, security, and semiconductor design solutions.",
                    "posted_at": posted_date
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            print("Collected jobs:", len(all_jobs))

            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "a.next")

                if not next_button.is_displayed():
                    break

                driver.execute_script("arguments[0].click();", next_button)

                wait.until(
                    lambda d: d.find_elements(
                        By.CSS_SELECTOR,
                        "li.search-results-list__list-item"
                    )[0].find_element(
                        By.CSS_SELECTOR,
                        "span.jobId"
                    ).text != first_job_before
                )

                page_number += 1
                time.sleep(2)

            except Exception:
                print("Pagination finished.")
                break

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Synopsys jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()
        driver.quit()

    return all_jobs


# =============================
# MAIN
# =============================

if __name__ == "__main__":

    jobs_data = scrape_synopsys_jobs()

    print("\nTotal jobs scraped:", len(jobs_data))

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