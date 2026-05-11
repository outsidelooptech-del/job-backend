import json
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from save_job import save_job
from database import get_connection


# =============================
# CONFIG
# =============================

COMPANY_NAME = "McKinsey"
COMPANY_LOGO = "https://img.logo.dev/mckinsey.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://www.mckinsey.com"
SEARCH_URL = "https://www.mckinsey.com/careers/search-jobs?countries=India&start="

OUTPUT_FILE = "mckinsey_jobs_india.json"

MAX_JOBS = 500
MAX_START = 100
STEP = 20


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
# DRIVER
# =============================

def setup_driver():

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    return driver


# =============================
# SCRAPER
# =============================

def scrape_mckinsey_jobs():

    conn = get_connection()
    cur = conn.cursor()

    driver = setup_driver()

    all_jobs = []
    seen_links = set()

    start = 0

    print("🚀 McKinsey Job Scraper Started...\n")

    try:
        while start <= MAX_START and len(all_jobs) < MAX_JOBS:

            print(f"\nOpening page starting at {start}")

            driver.get(SEARCH_URL + str(start))

            wait = WebDriverWait(driver, 20)

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//li[contains(@class,'job-listing')]")
                    )
                )
            except Exception:
                print("No more jobs found.")
                break

            time.sleep(3)

            job_cards = driver.find_elements(
                By.XPATH,
                "//li[contains(@class,'job-listing')]"
            )

            print("Jobs found on this page:", len(job_cards))

            if not job_cards:
                break

            for job in job_cards:

                if len(all_jobs) >= MAX_JOBS:
                    break

                try:
                    title_element = job.find_element(By.XPATH, ".//h2//a")

                    title = (
                        title_element.text
                        .strip()
                        .replace("Job title", "")
                        .strip()
                    ) or "Not Mentioned"

                    apply_link = title_element.get_attribute("href") or ""

                    if not apply_link:
                        continue

                    if not apply_link.startswith("http"):
                        apply_link = BASE_URL + apply_link

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    try:
                        interest = job.find_element(
                            By.XPATH,
                            ".//p[contains(@class,'interests')]"
                        ).text.replace("Job interest", "").strip()
                    except Exception:
                        interest = None

                    try:
                        location = job.find_element(
                            By.XPATH,
                            ".//div[contains(@class,'city')]"
                        ).text

                        location = location.replace(
                            "List of cities where this job is available",
                            ""
                        )

                        location = location.replace(
                            "This job is available in",
                            ""
                        ).strip()

                    except Exception:
                        location = "India"

                    keywords = list(set([
                        str(k)
                        for k in [
                            interest,
                            location,
                            f"Start {start}"
                        ]
                        if k
                    ]))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title,
                        "location": location or "India",
                        "apply_link": apply_link,
                        "keywords": keywords,

                        "source": "McKinsey Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location, title),
                        "job_type": detect_job_type(title),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": interest or "Not specified",
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "McKinsey & Company is a global management consulting firm providing strategy, operations, technology, analytics, and transformation consulting services.",
                        "posted_at": None
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping job due to error:", e)
                    continue

            print("Collected jobs:", len(all_jobs))

            start += STEP
            time.sleep(2)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} McKinsey jobs to database.")

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

    jobs_data = scrape_mckinsey_jobs()

    print("\n✅ Total Jobs Collected:", len(jobs_data))

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
