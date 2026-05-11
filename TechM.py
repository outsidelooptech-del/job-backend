import time
import json

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

COMPANY_NAME = "Tech Mahindra"
COMPANY_LOGO = "https://img.logo.dev/techmahindra.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

URL = "https://careers.techmahindra.com/Currentopportunity.aspx"
OUTPUT_FILE = "techmahindra_jobs.json"

MAX_JOBS = 500
MAX_PAGES = 100


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


def detect_experience(title, experience_text=""):
    text = f"{title or ''} {experience_text or ''}".lower()

    if "intern" in text:
        return "Internship"

    if "fresher" in text or "graduate" in text or "entry level" in text:
        return "Freshers"

    if experience_text:
        return experience_text

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
# DRIVER SETUP
# =============================

def setup_driver():

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")

    driver = webdriver.Chrome(options=options)

    return driver


# =============================
# SCRAPER
# =============================

def scrape_techmahindra_jobs():

    conn = get_connection()
    cur = conn.cursor()

    driver = setup_driver()
    wait = WebDriverWait(driver, 20)

    all_jobs = []
    seen_links = set()

    page = 1

    print("🚀 Scraping Tech Mahindra jobs...\n")

    try:
        driver.get(URL)

        while page <= MAX_PAGES and len(all_jobs) < MAX_JOBS:

            print(f"Scraping Page {page}")

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            ".paragraph--type--card-info-stand-tiles"
                        )
                    )
                )
            except Exception:
                print("No job cards found.")
                break

            time.sleep(2)

            job_cards = driver.find_elements(
                By.CSS_SELECTOR,
                ".paragraph--type--card-info-stand-tiles"
            )

            if not job_cards:
                print("No job cards on this page.")
                break

            for card in job_cards:

                if len(all_jobs) >= MAX_JOBS:
                    break

                try:
                    lines = [
                        line.strip()
                        for line in card.text.split("\n")
                        if line.strip()
                    ]

                    if len(lines) < 2:
                        continue

                    title = lines[1] or "Not Mentioned"

                    skill = ""
                    experience_text = ""
                    location = ""

                    for line in lines:
                        if "Skill Set" in line:
                            skill = line.split(":")[-1].strip()

                        if "Experience" in line:
                            experience_text = line.split(":")[-1].strip()

                        if "Location" in line:
                            location = line.split(":")[-1].strip()

                    apply_link = ""

                    try:
                        anchors = card.find_elements(By.TAG_NAME, "a")

                        for anchor in anchors:
                            href = anchor.get_attribute("href")

                            if href and "JobDetails.aspx" in href:
                                apply_link = href.strip()
                                break

                    except Exception:
                        apply_link = ""

                    if apply_link and not apply_link.startswith("http"):
                        apply_link = (
                            "https://careers.techmahindra.com/"
                            + apply_link
                        )

                    if not apply_link:
                        continue

                    if apply_link in seen_links:
                        continue

                    seen_links.add(apply_link)

                    keywords = list(set([
                        str(k)
                        for k in [
                            skill,
                            experience_text,
                            location,
                            f"Page {page}"
                        ]
                        if k
                    ]))

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title,
                        "location": location or "India",
                        "apply_link": apply_link,
                        "keywords": keywords,

                        "source": "Tech Mahindra Careers",
                        "company_logo": COMPANY_LOGO,
                        "work_mode": detect_work_mode(location, title),
                        "job_type": detect_job_type(title),
                        "experience": detect_experience(
                            title,
                            experience_text
                        ),
                        "education": "Not specified",
                        "department": skill or "Not specified",
                        "salary": "Not disclosed",
                        "job_description": skill or "",
                        "company_description": "Tech Mahindra is an Indian multinational technology company providing IT services, consulting, business process services, digital transformation, and enterprise solutions.",
                        "posted_at": "Not specified"
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping job due to error:", e)
                    continue

            print("Collected jobs:", len(all_jobs))

            try:
                job_cards = driver.find_elements(
                    By.CSS_SELECTOR,
                    ".paragraph--type--card-info-stand-tiles"
                )

                if not job_cards:
                    break

                old_first_job = job_cards[0].text

                next_button = driver.find_element(
                    By.XPATH,
                    "//a[text()='>>' and contains(@class,'page_enabled')]"
                )

                driver.execute_script("arguments[0].click();", next_button)

                wait.until(
                    lambda d: d.find_elements(
                        By.CSS_SELECTOR,
                        ".paragraph--type--card-info-stand-tiles"
                    )[0].text != old_first_job
                )

                page += 1
                time.sleep(2)

            except Exception:
                print("Pagination finished.")
                break

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Tech Mahindra jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()
        driver.quit()

    return all_jobs


# ============================
# MAIN
# ============================

if __name__ == "__main__":

    jobs = scrape_techmahindra_jobs()

    print("\nTotal Jobs Scraped:", len(jobs))

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

    print("✅ Saved to", OUTPUT_FILE)