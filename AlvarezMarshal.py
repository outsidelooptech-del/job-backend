import json
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from database import get_connection
from save_job import save_job


COMPANY_NAME = "Alvarez & Marsal"
COMPANY_LOGO = "https://img.logo.dev/alvarezandmarsal.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://careers.alvarezandmarsal.com/search/jobs/in?page={}"

MAX_LIMIT = 500


def detect_work_mode(location):
    if not location:
        return "Onsite"

    text = location.lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title):
    if not title:
        return "Full Time"

    text = title.lower()

    if "intern" in text:
        return "Internship"

    if "contract" in text:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def detect_experience(title):
    if not title:
        return "Not specified"

    text = title.lower()

    if "intern" in text:
        return "Internship"

    if "graduate" in text or "fresher" in text or "entry level" in text:
        return "Freshers"

    if "analyst" in text or "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "manager" in text or "director" in text or "lead" in text:
        return "5+ yrs"

    return "Not specified"


def fetch_alvarez_marsal_jobs():

    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 30)

    conn = get_connection()
    cur = conn.cursor()

    all_jobs = []
    seen_links = set()

    try:
        driver.get(BASE_URL.format(1))

        print("\n⚠️ Solve Cloudflare once, then press ENTER.")
        input()

        page = 1

        while page <= 50:

            if len(all_jobs) >= MAX_LIMIT:
                print(f"Reached {MAX_LIMIT} job limit. Stopping scraper.")
                break

            print(f"\nScraping {COMPANY_NAME} page {page}")

            driver.get(BASE_URL.format(page))

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".jobs-section__item")
                    )
                )
            except Exception:
                print("No jobs found. Stopping.")
                break

            jobs = driver.find_elements(
                By.CSS_SELECTOR,
                ".jobs-section__item"
            )

            if not jobs:
                break

            new_found = 0

            for job in jobs:

                if len(all_jobs) >= MAX_LIMIT:
                    break

                try:
                    title_el = job.find_element(By.CSS_SELECTOR, "h2 a")

                    title = title_el.text.strip()
                    apply_link = title_el.get_attribute("href")

                    if not apply_link:
                        continue

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)
                    new_found += 1

                    try:
                        location = job.find_element(
                            By.CSS_SELECTOR,
                            ".large-4.columns"
                        ).text.replace("\n", " ").strip()
                    except Exception:
                        location = "Not Mentioned"

                    try:
                        date_posted = job.find_element(
                            By.CSS_SELECTOR,
                            ".large-2.columns"
                        ).text.strip()
                    except Exception:
                        date_posted = None

                    keywords = list(filter(None, [
                        date_posted,
                        detect_experience(title)
                    ]))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title or "Not Mentioned",
                        "location": location or "Not Mentioned",
                        "apply_link": apply_link,
                        "keywords": list(set(keywords)),

                        "source": "Alvarez & Marsal Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location),
                        "job_type": detect_job_type(title),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": None,
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "Alvarez & Marsal is a global professional services firm specializing in advisory, business performance improvement and turnaround management.",
                        "posted_at": date_posted
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping job due to error:", e)
                    continue

            if new_found == 0:
                break

            page += 1

            time.sleep(random.uniform(2, 5))

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


if __name__ == "__main__":

    jobs = fetch_alvarez_marsal_jobs()

    with open(
        "alvarez_marsal_india_jobs.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Total jobs scraped: {len(jobs)}")