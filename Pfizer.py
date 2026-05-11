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

COMPANY_NAME = "Pfizer"
COMPANY_LOGO = "https://img.logo.dev/pfizer.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

URL = "https://www.pfizer.co.in/careers/search-results?langcode=en&region[0]=India&count=100&sort=latest#"
OUTPUT_FILE = "pfizer_india_jobs.json"

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

def scrape_pfizer_jobs():

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

    jobs_collected = []
    seen_links = set()

    print("🚀 Scraping Pfizer India jobs...\n")

    try:
        driver.get(URL)

        wait = WebDriverWait(driver, 20)

        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "td.job-posting")
            )
        )

        while len(jobs_collected) < MAX_JOBS:

            print("Scraping current loaded jobs...")

            rows = driver.find_elements(By.CSS_SELECTOR, "tbody tr")

            for row in rows:

                if len(jobs_collected) >= MAX_JOBS:
                    break

                try:
                    title_element = row.find_element(
                        By.CSS_SELECTOR,
                        "td.job-posting a"
                    )

                    title = title_element.text.strip() or "Not Mentioned"
                    apply_link = title_element.get_attribute("href") or ""

                    if not apply_link:
                        continue

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    tds = row.find_elements(By.TAG_NAME, "td")

                    category = tds[1].text.strip() if len(tds) > 1 else None
                    job_type_text = (
                        tds[2].text.strip().replace("\n", " | ")
                        if len(tds) > 2
                        else None
                    )
                    location = tds[3].text.strip() if len(tds) > 3 else "India"

                    keywords = list(set([
                        k for k in [
                            category,
                            job_type_text,
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

                        "source": "Pfizer Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location, title),
                        "job_type": detect_job_type(title, job_type_text),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": category or "Not specified",
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "Pfizer is a global pharmaceutical and biotechnology company focused on medicines, vaccines, research, and healthcare solutions.",
                        "posted_at": "Not specified"
                    }

                    jobs_collected.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping row due to error:", e)
                    continue

            print("Current total:", len(jobs_collected))

            if len(jobs_collected) >= MAX_JOBS:
                break

            try:
                load_more = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "button.button.button--bare.button--size--large"
                        )
                    )
                )

                old_count = len(
                    driver.find_elements(By.CSS_SELECTOR, "tbody tr")
                )

                driver.execute_script("arguments[0].click();", load_more)

                print("Loading more jobs...")

                wait.until(
                    lambda d: len(
                        d.find_elements(By.CSS_SELECTOR, "tbody tr")
                    ) > old_count
                )

                time.sleep(1)

            except Exception:
                print("No more Load More button found.")
                break

        conn.commit()

        print(f"\n✅ Saved {len(jobs_collected)} Pfizer jobs to database.")

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

    jobs_data = scrape_pfizer_jobs()

    print(f"\n✅ Total India Jobs Collected: {len(jobs_data)}")

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