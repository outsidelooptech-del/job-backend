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


BASE_URL = "https://careers.adobe.com/us/en/search-results"
KEYWORD = "India"
COMPANY_NAME = "Adobe"
COMPANY_LOGO = "https://img.logo.dev/adobe.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"


def clean_label_text(text):
    if not text:
        return None

    parts = [part.strip() for part in text.split("\n") if part.strip()]
    return parts[-1] if parts else None


def detect_work_mode(location):
    if not location:
        return "Onsite"

    text = location.lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, category):
    text = f"{title or ''} {category or ''}".lower()

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

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if "associate" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if "lead" in text or "manager" in text or "staff" in text:
        return "5+ yrs"

    return "Not specified"


def fetch_adobe_jobs(max_pages=50):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    conn = get_connection()
    cur = conn.cursor()

    wait = WebDriverWait(driver, 20)

    all_jobs = []
    seen_job_ids = set()

    print("Started fetching Adobe jobs...")

    try:
        for page in range(1, max_pages + 1):
            from_value = (page - 1) * 10

            if page == 1:
                url = f"{BASE_URL}?keywords={KEYWORD}"
            else:
                url = f"{BASE_URL}?keywords={KEYWORD}&from={from_value}&s=1"

            print(f"\nScraping Adobe page {page}")

            driver.get(url)

            try:
                wait.until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "div.job-title")
                    )
                )
            except Exception:
                print("No more Adobe jobs found.")
                break

            time.sleep(2)

            title_blocks = driver.find_elements(By.CSS_SELECTOR, "div.job-title")

            if not title_blocks:
                break

            for title_block in title_blocks:
                try:
                    title = title_block.find_element(
                        By.TAG_NAME, "span"
                    ).text.strip()

                    container = title_block.find_element(
                        By.XPATH, "./ancestor::li[1]"
                    )

                    # ---------- Location ----------
                    try:
                        raw_location = container.find_element(
                            By.CSS_SELECTOR, "span.job-location"
                        ).text

                        location = clean_label_text(raw_location)

                    except Exception:
                        location = "Not Mentioned"

                    # ---------- Category / Department ----------
                    try:
                        raw_category = container.find_element(
                            By.CSS_SELECTOR, "span.job-category"
                        ).text

                        category = clean_label_text(raw_category)

                    except Exception:
                        category = None

                    # ---------- Apply Link ----------
                    try:
                        raw_link = container.find_element(
                            By.CSS_SELECTOR,
                            "a[data-ph-at-id='apply-link']"
                        ).get_attribute("href")

                        job_id = raw_link

                        if raw_link and "jobSeqNo=" in raw_link:
                            job_id = raw_link.split("jobSeqNo=")[-1].split("&")[0]

                        if job_id in seen_job_ids:
                            continue

                        seen_job_ids.add(job_id)

                        apply_link = raw_link or "Not Mentioned"

                    except Exception:
                        apply_link = "Not Mentioned"

                    keywords = [category] if category else []

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title,
                        "location": location,
                        "apply_link": apply_link,
                        "keywords": keywords,

                        "source": "Adobe Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location),
                        "job_type": detect_job_type(title, category),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": category,
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "Adobe is a global software company known for creative, document, and digital experience products.",
                        "posted_at": None
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)
                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping job due to error:", e)
                    continue

            if len(title_blocks) < 10:
                break

        conn.commit()
        print("Finished saving Adobe jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()
        driver.quit()

    return all_jobs


if __name__ == "__main__":
    jobs = fetch_adobe_jobs()

    print(f"Total Jobs Collected: {len(jobs)}")

    with open("adobe_india_jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)

    print("Saved to adobe_india_jobs.json")