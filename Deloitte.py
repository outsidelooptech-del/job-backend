from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import json
import time

from save_job import save_job
from database import get_connection


COMPANY_NAME = "Deloitte"
COMPANY_LOGO = "https://img.logo.dev/deloitte.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://usijobs.deloitte.com/en_US/careersusi"
OUTPUT_FILE = "deloitte_india_jobs.json"


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(options=options)


def detect_work_mode(location, keywords=None):
    text = f"{location or ''} {' '.join(keywords or [])}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, keywords=None):
    text = f"{title or ''} {' '.join(keywords or [])}".lower()

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def detect_experience(title, keywords=None):
    text = f"{title or ''} {' '.join(keywords or [])}".lower()

    if "intern" in text:
        return "Internship"

    if "analyst" in text or "associate analyst" in text:
        return "0-2 yrs"

    if "consultant" in text:
        return "2+ yrs"

    if "senior" in text or "manager" in text or "lead" in text:
        return "5+ yrs"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    return "Not specified"


def fetch_deloitte_jobs():

    driver = setup_driver()
    wait = WebDriverWait(driver, 15)

    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    page = 1

    print("🚀 Deloitte Job Scraper Started...")

    try:
        driver.get(BASE_URL)
        time.sleep(3)

        while True:

            print(f"\nScraping Page {page} ...")

            try:
                wait.until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "article.article--result")
                    )
                )
            except TimeoutException:
                print("No job cards found. Stopping.")
                break

            time.sleep(2)

            job_cards = driver.find_elements(
                By.CSS_SELECTOR,
                "article.article--result"
            )

            print("Jobs Found:", len(job_cards))

            if not job_cards:
                break

            jobs_found = 0

            for job in job_cards:

                try:
                    title_element = job.find_element(
                        By.CSS_SELECTOR,
                        "h3 a.link"
                    )

                    title = title_element.text.strip()
                    apply_link = title_element.get_attribute("href")

                    if not apply_link:
                        continue

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    subtitle_parts = []

                    try:
                        subtitle_div = job.find_element(
                            By.CSS_SELECTOR,
                            "div.article__header__text__subtitle"
                        )

                        spans = subtitle_div.find_elements(By.TAG_NAME, "span")

                        subtitle_parts = [
                            s.text.strip() for s in spans if s.text.strip()
                        ]

                    except Exception:
                        subtitle_parts = []

                    location = subtitle_parts[-1] if subtitle_parts else "India"

                    keywords = []
                    if subtitle_parts:
                        keywords.extend(subtitle_parts[:-1])

                    keywords = list(set([k for k in keywords if k]))

                    department = keywords[0] if keywords else None

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title or "Not Mentioned",
                        "location": location or "India",
                        "apply_link": apply_link,
                        "keywords": keywords,

                        "source": "Deloitte USI Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location, keywords),
                        "job_type": detect_job_type(title, keywords),
                        "experience": detect_experience(title, keywords),
                        "education": "Not specified",
                        "department": department,
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "Deloitte is a global professional services firm providing consulting, audit, tax, risk advisory and technology services.",
                        "posted_at": None
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                    jobs_found += 1

                except Exception as e:
                    print("Error scraping job:", e)

            if jobs_found == 0:
                print("No jobs parsed. Stopping.")
                break

            try:
                next_button = driver.find_element(
                    By.CSS_SELECTOR,
                    "a.list-controls__pagination__item.paginationNextLink"
                )

                next_link = next_button.get_attribute("href")

                if not next_link:
                    break

                driver.get(next_link)

                page += 1
                time.sleep(3)

            except Exception:
                break

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Deloitte jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        driver.quit()
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs = fetch_deloitte_jobs()

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