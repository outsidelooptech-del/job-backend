import json
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from save_job import save_job
from database import get_connection


# =============================
# CONFIG
# =============================

COMPANY_NAME = "Stripe"
COMPANY_LOGO = "https://img.logo.dev/stripe.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

START_URL = "https://stripe.com/jobs/search?office_locations=Asia+Pacific--Bengaluru"
OUTPUT_FILE = "stripe_bengaluru_jobs.json"

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

def scrape_stripe_jobs():

    conn = get_connection()
    cur = conn.cursor()

    driver = setup_driver()
    wait = WebDriverWait(driver, 20)

    all_jobs = []

    seen_links = set()

    page_number = 1

    print("🚀 Scraping Stripe Bengaluru jobs...\n")

    try:
        driver.get(START_URL)

        while len(all_jobs) < MAX_JOBS:

            print(f"\nScraping Page {page_number}")

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "tr.TableRow")
                    )
                )
            except Exception:
                print("No job listings found.")
                break

            time.sleep(2)

            jobs = driver.find_elements(By.CSS_SELECTOR, "tr.TableRow")

            if not jobs:
                print("No job rows found.")
                break

            print("Jobs found:", len(jobs))

            for job in jobs:

                if len(all_jobs) >= MAX_JOBS:
                    break

                try:
                    title_element = job.find_element(
                        By.CSS_SELECTOR,
                        "a.JobsListings__link"
                    )

                    title = title_element.text.strip() or "Not Mentioned"
                    apply_link = title_element.get_attribute("href") or ""

                    if not apply_link:
                        continue

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                except Exception:
                    continue

                try:
                    department = job.find_element(
                        By.CSS_SELECTOR,
                        ".JobsListings__departmentsListItem"
                    ).text.strip()
                except Exception:
                    department = None

                try:
                    location = job.find_element(
                        By.CSS_SELECTOR,
                        "span.JobsListings__locationDisplayName"
                    ).text.strip()
                except Exception:
                    location = "Bengaluru"

                keywords = list(set([
                    str(k)
                    for k in [
                        department,
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

                    "source": "Stripe Careers",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": department or "Not specified",
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "Stripe is a global financial infrastructure and payments technology company that provides payment processing, billing, fraud prevention, and financial tools for businesses.",
                    "posted_at": "Not specified"
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            try:
                next_button = driver.find_element(
                    By.XPATH,
                    "//a[contains(@class,'JobsPagination__link') and contains(text(),'Next')]"
                )

                print("Next page found. Moving to next page...")

                driver.execute_script("arguments[0].click();", next_button)

                page_number += 1
                time.sleep(3)

            except Exception:
                print("No Next button found. Pagination finished.")
                break

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Stripe jobs to database.")

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

    jobs_data = scrape_stripe_jobs()

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