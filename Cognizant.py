import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from database import get_connection
from save_job import save_job


# ----------------------------
# CONFIG
# ----------------------------

BASE_URL = "https://careers.cognizant.com/india-en/jobs/"
COMPANY_NAME = "Cognizant"
COMPANY_LOGO = "https://img.logo.dev/cognizant.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

OUTPUT_FILE = "Cognizant_India_jobs.json"


# ----------------------------
# HELPERS
# ----------------------------

def detect_work_mode(location):
    text = (location or "").lower()

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
    text = (title or "").lower()

    if "intern" in text:
        return "Internship"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if "associate" in text or "programmer analyst trainee" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if (
        "manager" in text
        or "lead" in text
        or "architect" in text
        or "director" in text
    ):
        return "5+ yrs"

    return "Not specified"


# ----------------------------
# SCRAPER
# ----------------------------

def scrape_cognizant_jobs():

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    conn = get_connection()
    cur = conn.cursor()

    print("🚀 Cognizant Job Scraper Started...")

    all_jobs = []
    seen_links = set()
    max_pages = 20

    try:

        for page in range(1, max_pages + 1):

            url = (
                f"{BASE_URL}?page={page}"
                "&location=India&radius=100"
                "&cname=India&ccode=IN"
                "&pagesize=10#results"
            )

            print(f"\nScraping page {page}")

            driver.get(url)
            time.sleep(3)

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.card.card-job")
                    )
                )
            except Exception:
                print("No job listings found.")
                break

            job_cards = driver.find_elements(
                By.CSS_SELECTOR,
                "div.card.card-job"
            )

            if not job_cards:
                break

            jobs_found = 0

            for card in job_cards:

                try:
                    link_el = card.find_element(
                        By.CSS_SELECTOR,
                        "h2.card-title a"
                    )

                    title = link_el.text.strip()
                    apply_link = link_el.get_attribute("href")

                    if not title or not apply_link:
                        continue

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    job_id = card.get_attribute("data-id") or ""

                    meta_items = card.find_elements(
                        By.CSS_SELECTOR,
                        "ul.job-meta li"
                    )

                    location = meta_items[0].text.strip() if len(meta_items) > 0 else "India"
                    category = meta_items[1].text.strip() if len(meta_items) > 1 else None

                    keywords = list(set(filter(None, [
                        job_id,
                        category
                    ])))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title or "Not Mentioned",
                        "location": location or "India",
                        "apply_link": apply_link,
                        "keywords": keywords,

                        "source": "Cognizant Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location),
                        "job_type": detect_job_type(title, category),
                        "experience": detect_experience(title),
                        "education": "Not specified",
                        "department": category,
                        "salary": "Not disclosed",
                        "job_description": "",
                        "company_description": "Cognizant is a global technology services and consulting company helping businesses with digital transformation, cloud, AI, engineering and operations.",
                        "posted_at": None
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                    jobs_found += 1

                except Exception as e:
                    print("Skipping card:", e)

            if jobs_found == 0:
                print("No jobs parsed — stopping.")
                break

            time.sleep(1)

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Cognizant jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        driver.quit()
        cur.close()
        conn.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Scraped {len(all_jobs)} Cognizant jobs!")
    print("Saved to", OUTPUT_FILE)

    return all_jobs


# ----------------------------
# MAIN
# ----------------------------

if __name__ == "__main__":
    scrape_cognizant_jobs()