import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from database import get_connection
from save_job import save_job


# ===============================
# CONFIG
# ===============================

COMPANY_NAME = "Cisco"
COMPANY_LOGO = "https://img.logo.dev/cisco.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://careers.cisco.com/global/en/search-results"
OUTPUT_FILE = "cisco_jobs.json"


# ===============================
# HELPERS
# ===============================

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
        "lead" in text
        or "manager" in text
        or "principal" in text
        or "staff" in text
        or "architect" in text
    ):
        return "5+ yrs"

    return "Not specified"


# ===============================
# DRIVER SETUP
# ===============================

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(options=options)


# ===============================
# SCRAPER
# ===============================

def fetch_cisco_jobs():

    driver = setup_driver()
    wait = WebDriverWait(driver, 15)

    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    offset = 0
    page_size = 10
    max_pages = 12

    print(f"Started fetching {COMPANY_NAME} jobs...")

    try:

        while offset < page_size * max_pages:

            url = BASE_URL if offset == 0 else f"{BASE_URL}?from={offset}&s=1"

            print(f"\nScraping {COMPANY_NAME} jobs — offset={offset}")

            driver.get(url)

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "a[data-ph-at-id='job-link']")
                    )
                )
            except TimeoutException:
                print("No jobs found — stopping.")
                break

            job_cards = driver.find_elements(
                By.CSS_SELECTOR,
                "a[data-ph-at-id='job-link']"
            )

            if not job_cards:
                break

            new_found = 0

            for card in job_cards:

                try:
                    title = card.text.strip()
                    job_url = card.get_attribute("href")

                    if not job_url:
                        continue

                    if job_url in seen_links:
                        continue

                    seen_links.add(job_url)
                    new_found += 1

                    parent = card.find_element(
                        By.XPATH,
                        "./ancestor::div[contains(@class,'phw-posn-relative')]"
                    )

                    # ---------- Location ----------
                    location = ""

                    try:
                        location_container = parent.find_element(
                            By.CSS_SELECTOR,
                            "[data-ph-at-id='job-location']"
                        )

                        spans = location_container.find_elements(By.TAG_NAME, "span")
                        location = spans[-1].text.strip() if spans else ""

                    except Exception:
                        try:
                            location = parent.find_element(
                                By.CSS_SELECTOR,
                                "[data-ph-at-id='job-multi_location']"
                            ).text.strip()
                        except Exception:
                            location = ""

                    # ---------- Category / Department ----------
                    try:
                        category = parent.find_element(
                            By.CSS_SELECTOR,
                            "[data-ph-at-id='job-category'] span:last-child"
                        ).text.strip()
                    except Exception:
                        category = ""

                    # ---------- Job ID ----------
                    try:
                        job_id = parent.find_element(
                            By.CSS_SELECTOR,
                            "[data-ph-at-id='job-jobId'] span:last-child"
                        ).text.strip()
                    except Exception:
                        job_id = ""

                    keywords = list(set([
                        k for k in [category, job_id] if k
                    ]))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title or "Not Mentioned",
                        "location": location or "Not Mentioned",
                        "apply_link": job_url,
                        "keywords": keywords,

                        "source": "Cisco Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location),
                        "job_type": detect_job_type(title, category),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": category or None,
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "Cisco is a global technology company specializing in networking, cybersecurity, cloud, collaboration and enterprise technology solutions.",
                        "posted_at": None
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping card:", e)

            if new_found == 0:
                break

            offset += page_size
            time.sleep(1)

        conn.commit()

        print(f"Finished saving {COMPANY_NAME} jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()
        driver.quit()

    return all_jobs


# ===============================
# MAIN
# ===============================

if __name__ == "__main__":

    jobs = fetch_cisco_jobs()

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

    print(f"\n✅ Scraped {len(jobs)} {COMPANY_NAME} jobs!")
    print("Saved to", OUTPUT_FILE)