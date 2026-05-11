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


# =============================
# CONFIG
# =============================

COMPANY_NAME = "PwC"
COMPANY_LOGO = "https://img.logo.dev/pwc.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

URL = "https://www.pwc.in/careers/experienced-jobs/results.html?wdcountry=IND|BGD&wdjobsite=Global_Experienced_Careers&flds=jobreqid,title,location,jobsite,iso"
OUTPUT_FILE = "pwc_india_jobs.json"

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
# SCRAPER
# =============================

def scrape_pwc_jobs():

    conn = get_connection()
    cur = conn.cursor()

    options = webdriver.ChromeOptions()
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

    wait = WebDriverWait(driver, 15)

    jobs_collected = []
    seen_links = set()

    print("🚀 Fetching PwC India jobs...\n")

    try:
        driver.get(URL)

        while len(jobs_collected) < MAX_JOBS:

            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "tr[data-index]")
                )
            )

            rows = driver.find_elements(By.CSS_SELECTOR, "tr[data-index]")

            if not rows:
                print("No job rows found.")
                break

            for row in rows:

                if len(jobs_collected) >= MAX_JOBS:
                    break

                try:
                    cols = row.find_elements(By.TAG_NAME, "td")

                    if len(cols) < 2:
                        continue

                    link_element = cols[0].find_element(By.TAG_NAME, "a")

                    title = link_element.text.strip() or "Not Mentioned"
                    apply_link = link_element.get_attribute("href") or ""
                    location = cols[1].text.strip() or "India"

                    if not apply_link:
                        continue

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    keywords = list(set([
                        k for k in [
                            location,
                            "Experienced Careers",
                            "India"
                        ]
                        if k
                    ]))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title,
                        "location": location,
                        "apply_link": apply_link,
                        "keywords": keywords,

                        "source": "PwC Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location, title),
                        "job_type": detect_job_type(title),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": "Not specified",
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "PwC is a global professional services network providing assurance, advisory, consulting, tax, and business transformation services.",
                        "posted_at": "Not specified"
                    }

                    jobs_collected.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping row due to error:", e)
                    continue

            print(f"Collected {len(jobs_collected)} jobs")

            try:
                next_button = driver.find_element(
                    By.XPATH,
                    "//a[@aria-label='next page']"
                )

                parent_li = next_button.find_element(By.XPATH, "./..")

                if "disabled" in parent_li.get_attribute("class"):
                    print("Reached last page.")
                    break

                driver.execute_script("arguments[0].click();", next_button)

                time.sleep(2)

            except Exception:
                print("No next button found. Ending.")
                break

        conn.commit()

        print(f"\n✅ Saved {len(jobs_collected)} PwC jobs to database.")

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

    jobs_data = scrape_pwc_jobs()

    print(f"\n✅ Total Jobs Collected: {len(jobs_data)}")

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