import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from database import get_connection
from save_job import save_job


BASE_URL = "https://aecom.jobs/locations/ind/jobs/"
COMPANY_NAME = "AECOM"
COMPANY_LOGO = "https://img.logo.dev/aecom.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"


def detect_work_mode(location):
    if not location:
        return "Onsite"

    text = location.lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, keywords):
    text = f"{title or ''} {' '.join(keywords or [])}".lower()

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

    if "graduate" in text or "fresher" in text:
        return "Freshers"

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "manager" in text or "lead" in text:
        return "5+ yrs"

    return "Not specified"


def fetch_aecom_india_jobs():

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    conn = get_connection()
    cur = conn.cursor()

    wait = WebDriverWait(driver, 20)

    all_jobs = []
    seen_links = set()

    print("Started fetching AECOM jobs...")

    try:

        driver.get(BASE_URL)

        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "li.border-gray-light")
            )
        )

        # =========================
        # LOAD ALL JOBS
        # =========================
        while True:

            job_cards = driver.find_elements(
                By.CSS_SELECTOR,
                "li.border-gray-light"
            )

            current_count = len(job_cards)

            try:
                more_button = driver.find_element(
                    By.XPATH,
                    "//button[@aria-label='Load more jobs']"
                )

                driver.execute_script(
                    "arguments[0].scrollIntoView(true);",
                    more_button
                )

                time.sleep(1)

                driver.execute_script(
                    "arguments[0].click();",
                    more_button
                )

                wait.until(
                    lambda d: len(
                        d.find_elements(
                            By.CSS_SELECTOR,
                            "li.border-gray-light"
                        )
                    ) > current_count
                )

            except Exception:
                break

        time.sleep(2)

        job_cards = driver.find_elements(
            By.CSS_SELECTOR,
            "li.border-gray-light"
        )

        print(f"Found {len(job_cards)} AECOM jobs")

        for job in job_cards:

            try:
                title = job.find_element(
                    By.TAG_NAME,
                    "h2"
                ).text.strip()

                location = job.find_element(
                    By.XPATH,
                    ".//h2/following::div[1]"
                ).text.strip()

                apply_link = job.find_element(
                    By.TAG_NAME,
                    "a"
                ).get_attribute("href")

                if not apply_link:
                    continue

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)

                keywords = []

                # =========================
                # CAREER AREA
                # =========================
                try:
                    career_area = job.find_element(
                        By.XPATH,
                        ".//span[text()='Career Area:']/following-sibling::span"
                    ).text.strip()

                    if career_area:
                        keywords.append(career_area)

                except Exception:
                    career_area = None

                # =========================
                # BUSINESS LINE
                # =========================
                try:
                    business_line = job.find_element(
                        By.XPATH,
                        ".//span[text()='Business Line:']/following-sibling::span"
                    ).text.strip()

                    if business_line:
                        keywords.append(business_line)

                except Exception:
                    business_line = None

                keywords = list(set(keywords))

                # =========================
                # JOB DATA
                # =========================
                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": keywords,

                    "source": "AECOM Careers",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location),
                    "job_type": detect_job_type(title, keywords),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": career_area or business_line,
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "AECOM is a global infrastructure consulting firm delivering professional services across transportation, buildings, water, environment and energy.",
                    "posted_at": None
                }

                all_jobs.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            except Exception as e:
                print("Skipping job due to error:", e)
                continue

        conn.commit()

        print("Finished saving AECOM jobs to database.")

    finally:
        cur.close()
        conn.close()
        driver.quit()

    return all_jobs


if __name__ == "__main__":

    jobs = fetch_aecom_india_jobs()

    print(f"Total Jobs Collected: {len(jobs)}")

    with open("aecom_india_jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)

    print("Saved to aecom_india_jobs.json")