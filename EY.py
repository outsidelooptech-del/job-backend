import time
import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

from save_job import save_job
from database import get_connection


# =============================
# CONFIG
# =============================

COMPANY_NAME = "EY"
COMPANY_LOGO = "https://img.logo.dev/ey.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_PAGE_1 = "https://careers.ey.com/search/?createNewAlert=false&q=&optionsFacetsDD_customfield1=&optionsFacetsDD_country=IN&optionsFacetsDD_city="
BASE_PAGE_2 = "https://careers.ey.com/search/?q=&sortColumn=referencedate&sortDirection=desc&optionsFacetsDD_country=IN&startrow="

OUTPUT_FILE = "ey_jobs.json"

MAX_JOBS = 500
PAGE_SIZE = 25
MAX_PAGES = 40


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

    driver = webdriver.Chrome(options=options)

    return driver


# =============================
# SCRAPER
# =============================

def scrape_ey_jobs():

    conn = get_connection()
    cur = conn.cursor()

    driver = setup_driver()

    jobs = []
    seen_links = set()
    page_index = 0

    print("🚀 Scraping EY India jobs...\n")

    try:
        while len(jobs) < MAX_JOBS:

            if page_index == 0:
                url = BASE_PAGE_1
            else:
                startrow = page_index * PAGE_SIZE
                url = BASE_PAGE_2 + str(startrow)

            print("Scraping:", url)

            driver.get(url)
            time.sleep(3)

            rows = driver.find_elements(By.CSS_SELECTOR, "tr.data-row")

            if not rows:
                print("No rows found.")
                break

            for row in rows:

                if len(jobs) >= MAX_JOBS:
                    break

                try:
                    title_element = row.find_element(
                        By.CSS_SELECTOR,
                        "a.jobTitle-link"
                    )

                    title = title_element.text.strip() or "Not Mentioned"
                    href = title_element.get_attribute("href") or ""

                    if not href:
                        continue

                    if href.startswith("http"):
                        apply_link = href
                    else:
                        apply_link = "https://careers.ey.com" + href

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    try:
                        location = row.find_element(
                            By.CSS_SELECTOR,
                            "span.jobLocation"
                        ).text.strip()
                    except Exception:
                        location = "India"

                    keywords = list(set([
                        str(k)
                        for k in [
                            location,
                            f"Page {page_index + 1}",
                            "EY Careers"
                        ]
                        if k
                    ]))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title,
                        "location": location or "India",
                        "apply_link": apply_link,
                        "keywords": keywords,

                        "source": "EY Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location, title),
                        "job_type": detect_job_type(title),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": "Not specified",
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "EY is a global professional services organization providing assurance, consulting, strategy, tax, technology, and business transformation services.",
                        "posted_at": None
                    }

                    jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping row due to error:", e)
                    continue

            print("Collected jobs:", len(jobs))

            page_index += 1

            if page_index > MAX_PAGES:
                break

        conn.commit()

        print(f"\n✅ Saved {len(jobs)} EY jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()
        driver.quit()

    return jobs


# =============================
# MAIN
# =============================

if __name__ == "__main__":

    jobs = scrape_ey_jobs()

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

    print("✅ Saved to", OUTPUT_FILE)
