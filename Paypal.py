import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

from save_job import save_job
from database import get_connection


COMPANY_NAME = "PayPal"
COMPANY_LOGO = "https://img.logo.dev/paypal.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

URL = "https://paypal.eightfold.ai/careers?start=0&location=India&pid=274917281549&sort_by=distance&filter_include_remote=1"
OUTPUT_FILE = "paypal_india_jobs.json"

MAX_JOBS = 500


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


def scrape_paypal_jobs():

    conn = get_connection()
    cur = conn.cursor()

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    jobs_collected = []
    seen_ids = set()
    seen_links = set()

    print("🚀 Fetching PayPal India jobs...\n")

    try:
        driver.get(URL)
        time.sleep(5)

        last_height = driver.execute_script("return document.body.scrollHeight")

        while len(jobs_collected) < MAX_JOBS:

            job_cards = driver.find_elements(
                By.CSS_SELECTOR,
                "div[data-test-id='job-listing']"
            )

            if not job_cards:
                print("No job cards found.")
                break

            for card in job_cards:

                if len(jobs_collected) >= MAX_JOBS:
                    break

                try:
                    title = card.find_element(
                        By.CSS_SELECTOR,
                        ".title-1aNJK"
                    ).text.strip()
                except Exception:
                    title = "Not Mentioned"

                try:
                    job_link_element = card.find_element(By.TAG_NAME, "a")
                    job_url = job_link_element.get_attribute("href")
                    job_id = job_url.split("/")[-1] if job_url else ""
                except Exception:
                    job_url = ""
                    job_id = ""

                if not job_url:
                    continue

                if job_id in seen_ids or job_url in seen_links:
                    continue

                seen_ids.add(job_id)
                seen_links.add(job_url)

                try:
                    fields = card.find_elements(
                        By.CSS_SELECTOR,
                        ".fieldValue-3kEar"
                    )

                    location = fields[0].text.strip() if len(fields) > 0 else "India"
                    department = fields[1].text.strip() if len(fields) > 1 else None
                except Exception:
                    location = "India"
                    department = None

                try:
                    posted = card.find_element(
                        By.CSS_SELECTOR,
                        ".subData-13Lm1"
                    ).text.strip()
                except Exception:
                    posted = None

                keywords = list(set([
                    k for k in [job_id, department, posted] if k
                ]))

                job_data = {
                    "company": COMPANY_NAME,
                    "title": title,
                    "location": location,
                    "apply_link": job_url,
                    "keywords": keywords,

                    "source": "PayPal Eightfold Careers",
                    "company_logo": COMPANY_LOGO,
                    "work_mode": detect_work_mode(location, title),
                    "job_type": detect_job_type(title),
                    "experience": detect_experience(title),
                    "education": "Not specified",
                    "department": department,
                    "salary": "Not disclosed",
                    "job_description": "",
                    "company_description": "PayPal is a global digital payments company providing online payment, checkout, wallet and financial technology services.",
                    "posted_at": posted
                }

                jobs_collected.append(job_data)

                print("Saving:", title)

                save_job(job_data, cur)

            print(f"Collected {len(jobs_collected)} jobs...")

            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

            time.sleep(3)

            new_height = driver.execute_script(
                "return document.body.scrollHeight"
            )

            if new_height == last_height:
                break

            last_height = new_height

        conn.commit()

        print(f"\n✅ Saved {len(jobs_collected)} PayPal jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()
        driver.quit()

    return jobs_collected


if __name__ == "__main__":

    jobs_data = scrape_paypal_jobs()

    print(f"\nTotal jobs collected: {len(jobs_data)}")

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

    print("Saved to", OUTPUT_FILE)