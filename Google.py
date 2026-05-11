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

COMPANY_NAME = "Google"
COMPANY_LOGO = "https://img.logo.dev/google.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://www.google.com/about/careers/applications/jobs/results?location=India"

OUTPUT_FILE = "google_jobs.json"

PAGES_TO_SCRAPE = 3
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


def detect_experience(title, experience_text=""):
    text = f"{title or ''} {experience_text or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if experience_text:
        return experience_text

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
    options.add_argument("--disable-notifications")
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

def scrape_google_jobs():

    conn = get_connection()
    cur = conn.cursor()

    driver = setup_driver()

    all_jobs = []
    seen_links = set()

    print("\n🚀 Google Jobs Scraper Started...\n")

    try:
        for page in range(1, PAGES_TO_SCRAPE + 1):

            if len(all_jobs) >= MAX_JOBS:
                break

            print(f"\nScraping Page {page}...")

            driver.get(f"{BASE_URL}&page={page}")

            time.sleep(5)

            for _ in range(6):
                driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);"
                )
                time.sleep(2)

            cards = driver.find_elements(By.CSS_SELECTOR, "li.lLd3Je")

            print("Total job cards found:", len(cards))

            if not cards:
                continue

            for card in cards:

                if len(all_jobs) >= MAX_JOBS:
                    break

                try:
                    title = card.find_element(
                        By.CSS_SELECTOR,
                        "h3.QJPWVe"
                    ).text.strip() or "Not Mentioned"

                    apply_link = card.find_element(
                        By.CSS_SELECTOR,
                        "a.WpHeLc"
                    ).get_attribute("href") or ""

                    if not apply_link:
                        continue

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    try:
                        location = card.find_element(
                            By.CSS_SELECTOR,
                            "span.r0wTof"
                        ).text.strip()
                    except Exception:
                        location = "India"

                    try:
                        experience_text = card.find_element(
                            By.CSS_SELECTOR,
                            "span.wVSTAb"
                        ).text.strip()
                    except Exception:
                        experience_text = None

                    keywords = list(set([
                        str(k)
                        for k in [
                            experience_text,
                            location,
                            f"Page {page}",
                            "Google Careers"
                        ]
                        if k
                    ]))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title,
                        "location": location or "India",
                        "apply_link": apply_link,
                        "keywords": keywords,

                        "source": "Google Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location, title),
                        "job_type": detect_job_type(title),
                        "experience": detect_experience(
                            title,
                            experience_text
                        ),
                        "education": "Not specified",
                        "department": "Not specified",
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "Google is a global technology company focused on search, advertising, cloud computing, software, AI, hardware, and internet services.",
                        "posted_at": None
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping job due to error:", e)
                    continue

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Google jobs to database.")

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

    jobs_data = scrape_google_jobs()

    print("\n✅ Total Jobs Scraped:", len(jobs_data))

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

    print("\n📂 Saved Successfully:", OUTPUT_FILE)
