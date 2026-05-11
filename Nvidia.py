import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from save_job import save_job
from database import get_connection


# ----------------------------
# CONFIG
# ----------------------------

COMPANY_NAME = "NVIDIA"
COMPANY_LOGO = "https://img.logo.dev/nvidia.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

URL = "https://nvidia.eightfold.ai/careers?location=India&sort_by=distance&filter_include_remote=1"
OUTPUT_FILE = "nvidia_india_jobs.json"

MAX_JOBS = 500


# ----------------------------
# HELPERS
# ----------------------------

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
        or "staff" in text
    ):
        return "5+ yrs"

    return "Not specified"


# ----------------------------
# SCRAPER
# ----------------------------

def scrape_nvidia_jobs():

    conn = get_connection()
    cur = conn.cursor()

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    print("🚀 Opening NVIDIA Careers page...\n")

    jobs = []
    seen_links = set()
    previous_count = 0

    try:
        driver.get(URL)

        wait = WebDriverWait(driver, 10)
        time.sleep(6)

        while len(jobs) < MAX_JOBS:

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'div[data-test-id="job-listing"]')
                    )
                )
            except Exception:
                print("No job cards found. Stopping.")
                break

            job_cards = driver.find_elements(
                By.CSS_SELECTOR,
                'div[data-test-id="job-listing"]'
            )

            if not job_cards:
                print("No jobs found.")
                break

            for card in job_cards:

                if len(jobs) >= MAX_JOBS:
                    break

                try:
                    title = card.find_element(
                        By.XPATH,
                        './/div[contains(@class,"title")]'
                    ).text.strip()
                except Exception:
                    title = "Not Mentioned"

                try:
                    fields = card.find_elements(
                        By.XPATH,
                        './/div[contains(@class,"fieldValue")]'
                    )

                    job_id = fields[0].text.strip() if len(fields) > 0 else ""
                    location = fields[1].text.strip() if len(fields) > 1 else "India"

                except Exception:
                    job_id = ""
                    location = "India"

                try:
                    posted = card.find_element(
                        By.XPATH,
                        './/div[contains(@class,"subData")]'
                    ).text.strip()
                except Exception:
                    posted = None

                try:
                    link = card.find_element(
                        By.XPATH,
                        './/a[contains(@class,"r-link")]'
                    ).get_attribute("href")

                    if link and link.startswith("/"):
                        link = "https://nvidia.eightfold.ai" + link

                except Exception:
                    link = ""

                if not link:
                    continue

                if link in seen_links:
                    continue

                seen_links.add(link)

                keywords = list(set([
                    k for k in [job_id, posted] if k
                ]))

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title or "Not Mentioned",
                    "location": location or "India",
                    "apply_link": link,
                    "keywords": keywords,

                    "source": "NVIDIA Eightfold Careers",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": None,
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "NVIDIA is a global technology company known for GPUs, AI computing, data center platforms, gaming and accelerated computing.",
                    "posted_at": posted
                }

                jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            print(f"Collected {len(jobs)} jobs so far...")

            if len(jobs) >= MAX_JOBS:
                break

            if len(jobs) == previous_count:
                print("No new jobs found. Stopping.")
                break

            previous_count = len(jobs)

            try:
                next_button = driver.find_element(
                    By.CSS_SELECTOR,
                    'button[aria-label="Next jobs"]'
                )

                if next_button.get_attribute("aria-disabled") == "true":
                    print("Reached last page.")
                    break

                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(4)

            except Exception:
                print("Next button not found.")
                break

        conn.commit()

        print(f"\n✅ Saved {len(jobs)} NVIDIA jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()
        driver.quit()

    return jobs


# ----------------------------
# MAIN
# ----------------------------

if __name__ == "__main__":

    jobs_data = scrape_nvidia_jobs()

    print(f"\n✅ Total jobs collected: {len(jobs_data)}")

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