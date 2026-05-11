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

COMPANY_NAME = "Siemens"
COMPANY_LOGO = "https://img.logo.dev/siemens.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://jobs.siemens.com/en_US/externaljobs/SearchJobs/?42386=%5B812053%5D&42386_format=17546&listFilterMode=1&folderRecordsPerPage=50&folderOffset={}"
OUTPUT_FILE = "siemens_india_jobs.json"

MAX_JOBS = 500


# =============================
# HELPERS
# =============================

def safe_get(card, selector):
    elements = card.find_elements(By.CSS_SELECTOR, selector)
    return elements[0].text.strip() if elements else ""


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
# SCRAPER
# =============================

def scrape_siemens_jobs():

    conn = get_connection()
    cur = conn.cursor()

    offset = 0

    all_jobs = []
    seen_ids = set()
    seen_links = set()

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    print("🚀 Fetching Siemens India jobs...\n")

    try:
        while len(all_jobs) < MAX_JOBS:

            url = BASE_URL.format(offset)

            print("Loading:", url)

            driver.get(url)

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "article.article")
                    )
                )
            except Exception:
                print("No more jobs found.")
                break

            job_cards = driver.find_elements(By.CSS_SELECTOR, "article.article")

            if not job_cards:
                print("No job cards on this page.")
                break

            for card in job_cards:

                if len(all_jobs) >= MAX_JOBS:
                    break

                try:
                    title_element = card.find_elements(By.CSS_SELECTOR, "h3 a")

                    if not title_element:
                        continue

                    title = title_element[0].text.strip() or "Not Mentioned"
                    apply_link = title_element[0].get_attribute("href") or ""

                    city = safe_get(card, ".list-item-jobCity")
                    state = safe_get(card, ".list-item-jobState")
                    country = safe_get(card, ".list-item-jobCountry")

                    job_id = (
                        safe_get(card, ".list-item-jobId")
                        .replace("Job ID:", "")
                        .strip()
                    )

                    family = safe_get(card, ".list-item-family")

                    if not title or not apply_link:
                        continue

                    if job_id in seen_ids or apply_link in seen_links:
                        continue

                    seen_ids.add(job_id)
                    seen_links.add(apply_link)

                    location = ", ".join(
                        filter(None, [city, state, country])
                    ) or "India"

                    keywords = list(set([
                        str(k)
                        for k in [
                            job_id,
                            family,
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

                        "source": "Siemens Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location, title),
                        "job_type": detect_job_type(title),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": family or "Not specified",
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "Siemens is a global technology company focused on automation, digitalization, smart infrastructure, mobility, energy, software, and industrial solutions.",
                        "posted_at": "Not specified"
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping job due to error:", e)
                    continue

            print("Collected so far:", len(all_jobs))

            offset += 50
            time.sleep(2)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Siemens jobs to database.")

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

    jobs_data = scrape_siemens_jobs()

    print("Final Total Jobs:", len(jobs_data))

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