import json
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from database import get_connection
from save_job import save_job


# ==========================
# CONFIG
# ==========================

BASE_URL = "https://cummins.jobs/jobs/?location=India"
COMPANY_NAME = "Cummins"

COMPANY_LOGO = "https://img.logo.dev/cummins.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

OUTPUT_FILE = "Cummins_India_jobs.json"


# ==========================
# HELPERS
# ==========================

def detect_work_mode(location, work_type):
    text = f"{location or ''} {work_type or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, work_type):
    text = f"{title or ''} {work_type or ''}".lower()

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

    if "graduate" in text or "fresher" in text:
        return "Freshers"

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if (
        "manager" in text
        or "lead" in text
        or "director" in text
        or "principal" in text
    ):
        return "5+ yrs"

    return "Not specified"


# ==========================
# BROWSER SETUP
# ==========================

def setup_driver():

    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(options=options)


# ==========================
# SCRAPER
# ==========================

def scrape_cummins_jobs():

    driver = setup_driver()
    wait = WebDriverWait(driver, 20)

    conn = get_connection()
    cur = conn.cursor()

    all_jobs = []
    seen_links = set()

    page = 1
    max_pages = 30

    print("🚀 Cummins Job Scraper Started...")

    try:

        while page <= max_pages:

            url = f"{BASE_URL}&page={page}"

            print(f"\nScraping Cummins jobs — page {page}")

            driver.get(url)

            try:
                wait.until(
                    lambda d: any(
                        e.text.strip() != ""
                        for e in d.find_elements(
                            By.CSS_SELECTOR,
                            "section h2.bold.text-primary"
                        )
                    )
                )

            except Exception:
                print("No more jobs found — stopping.")
                break

            time.sleep(2)

            job_sections = driver.find_elements(
                By.CSS_SELECTOR,
                "section"
            )

            if not job_sections:
                break

            jobs_found_this_page = 0

            for section in job_sections:

                try:
                    link = section.find_element(By.CSS_SELECTOR, "a")
                    job_url = link.get_attribute("href")

                    if not job_url:
                        continue

                    if job_url in seen_links:
                        continue

                    seen_links.add(job_url)

                    title_el = section.find_element(
                        By.CSS_SELECTOR,
                        "h2.bold.text-primary"
                    )

                    title = title_el.text.strip()

                    if not title:
                        continue

                    meta_divs = section.find_elements(
                        By.CSS_SELECTOR,
                        "div.text-base"
                    )

                    location = (
                        meta_divs[0].text.strip()
                        if len(meta_divs) > 0
                        else "India"
                    )

                    work_type = (
                        meta_divs[1].text.strip()
                        if len(meta_divs) > 1
                        else ""
                    )

                    keywords = []

                    if work_type:
                        keywords.append(work_type)

                    keywords = list(set(keywords))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title,
                        "location": location,
                        "apply_link": job_url,
                        "keywords": keywords,

                        "source": "Cummins Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location, work_type),
                        "job_type": detect_job_type(title, work_type),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": None,
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "Cummins is a global power solutions company specializing in engines, power systems, components and clean energy technologies.",
                        "posted_at": None
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                    jobs_found_this_page += 1

                except Exception as e:
                    print("Skipping card:", e)

            if jobs_found_this_page == 0:
                print("No jobs parsed — stopping.")
                break

            page += 1
            time.sleep(1)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Cummins jobs to database.")

    except Exception as e:

        conn.rollback()
        print("Fatal error:", e)

    finally:

        driver.quit()

        cur.close()
        conn.close()

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            all_jobs,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(f"\n✅ Scraped {len(all_jobs)} Cummins jobs!")
    print("Saved to", OUTPUT_FILE)

    return all_jobs


# ==========================
# MAIN
# ==========================

if __name__ == "__main__":

    scrape_cummins_jobs()