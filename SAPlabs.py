import time
import json
import math

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from save_job import save_job
from database import get_connection


# ==============================
# CONFIG
# ==============================

COMPANY_NAME = "SAP"
COMPANY_LOGO = "https://img.logo.dev/sap.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://jobs.sap.com/go/India/8807201/"
BASE_DOMAIN = "https://jobs.sap.com"

OUTPUT_FILE = "sap_india_jobs.json"

MAX_JOBS = 500


# ==============================
# HELPERS
# ==============================

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


# ==============================
# DRIVER SETUP
# ==============================

def setup_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")

    driver = webdriver.Chrome(options=options)

    return driver


# ==============================
# SCRAPER
# ==============================

def scrape_sap_jobs():

    conn = get_connection()
    cur = conn.cursor()

    driver = setup_driver()
    wait = WebDriverWait(driver, 15)

    all_jobs = []
    seen_links = set()

    print("🚀 Scraping SAP India jobs...\n")

    try:
        driver.get(BASE_URL)

        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "tr.data-row")
            )
        )

        # ==============================
        # GET TOTAL PAGES
        # ==============================

        try:
            last_page_element = driver.find_element(
                By.CSS_SELECTOR,
                "a.paginationItemLast"
            )

            last_page_href = last_page_element.get_attribute("href")

            last_offset = int(
                last_page_href.split("/8807201/")[1].split("/")[0]
            )

            jobs_per_page = len(
                driver.find_elements(By.CSS_SELECTOR, "tr.data-row")
            )

            total_pages = math.ceil(last_offset / jobs_per_page) + 1

        except Exception:
            total_pages = 1

        print(f"Estimated Total Pages: {total_pages}\n")

        # ==============================
        # LOOP THROUGH PAGES
        # ==============================

        for page in range(total_pages):

            if len(all_jobs) >= MAX_JOBS:
                break

            if page != 0:
                page_url = (
                    f"{BASE_URL}{page * 25}/"
                    "?q=&sortColumn=referencedate"
                    "&sortDirection=desc&scrollToTable=true"
                )

                driver.get(page_url)

                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "tr.data-row")
                    )
                )

            time.sleep(2)

            job_rows = driver.find_elements(By.CSS_SELECTOR, "tr.data-row")

            print(f"Page {page + 1} | Jobs Found: {len(job_rows)}")

            for row in job_rows:

                if len(all_jobs) >= MAX_JOBS:
                    break

                try:
                    title_element = row.find_element(
                        By.CSS_SELECTOR,
                        "a.jobTitle-link"
                    )

                    title = title_element.text.strip() or "Not Mentioned"
                    apply_link = title_element.get_attribute("href") or ""

                    if not apply_link:
                        continue

                    if not apply_link.startswith("http"):
                        apply_link = BASE_DOMAIN + apply_link

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    try:
                        location = row.find_element(
                            By.CSS_SELECTOR,
                            "td.colLocation span.jobLocation"
                        ).text.strip().replace("\n", " ")
                    except Exception:
                        location = "India"

                    job_id = (
                        apply_link.split("/")[-2]
                        if "/" in apply_link
                        else apply_link
                    )

                    keywords = list(set([
                        str(k)
                        for k in [
                            job_id,
                            location,
                            f"Page {page + 1}"
                        ]
                        if k
                    ]))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title,
                        "location": location,
                        "apply_link": apply_link,
                        "keywords": keywords,

                        "source": "SAP Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location, title),
                        "job_type": detect_job_type(title),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": "Not specified",
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "SAP is a global enterprise software company known for ERP, cloud, analytics, business technology platform, and enterprise application solutions.",
                        "posted_at": "Not specified"
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping row due to error:", e)
                    continue

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} SAP jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()
        driver.quit()

    return all_jobs


# ==============================
# MAIN
# ==============================

if __name__ == "__main__":

    jobs = scrape_sap_jobs()

    print("\nTotal Jobs Scraped:", len(jobs))

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

    print("✅ Saved:", OUTPUT_FILE)