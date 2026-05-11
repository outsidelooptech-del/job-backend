import json
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

from save_job import save_job
from database import get_connection


# =============================
# CONFIG
# =============================

START_URL = "https://www.nestle.in/jobs/search-jobs?country=IN&keyword=&page=%2C1"

MAX_PAGES = 100
COMPANY_NAME = "Nestle"

OUTPUT_FILE = "nestle_india_jobs.json"

COMPANY_LOGO = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/Nestl%C3%A9.svg/512px-Nestl%C3%A9.svg.png"


# =============================
# SCRAPER
# =============================

def scrape_nestle_jobs():

    options = uc.ChromeOptions()

    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = uc.Chrome(
        version_main=145,
        options=options
    )

    wait = WebDriverWait(driver, 30)

    # ✅ OPEN DB CONNECTION ONCE
    conn = get_connection()
    cur = conn.cursor()

    print(f"🚀 Scraping {COMPANY_NAME} India jobs...\n")

    driver.get(START_URL)

    all_jobs = []
    visited_links = set()

    page_number = 1
    page_count = 0

    try:

        while True:

            print(f"Scraping Page {page_number}...")

            try:
                wait.until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            "div.jobs-container.views-row"
                        )
                    )
                )
            except:
                print("No job cards found or blocked.")
                break

            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, "html.parser")

            job_cards = soup.select(
                "div.jobs-container.views-row"
            )

            if not job_cards:
                break

            for card in job_cards:

                try:

                    title_element = card.select_one(
                        "div.jobs-title a"
                    )

                    if not title_element:
                        continue

                    title = title_element.text.strip()

                    apply_link = title_element.get("href", "").strip()

                    if not apply_link:
                        continue

                    if apply_link.startswith("/"):
                        apply_link = (
                            "https://www.nestle.in"
                            + apply_link
                        )

                    if apply_link in visited_links:
                        continue

                    visited_links.add(apply_link)

                    business = card.select_one(
                        "div.jobs-business"
                    )

                    business = (
                        business.text.strip()
                        if business else ""
                    )

                    job_type = card.select_one(
                        "div.jobs-type small"
                    )

                    job_type = (
                        job_type.text.strip()
                        if job_type else ""
                    )

                    location = card.select_one(
                        "div.jobs-location small"
                    )

                    location = (
                        location.text.strip()
                        if location else ""
                    )

                    career_area = card.select_one(
                        "div.jobs-career-area small"
                    )

                    career_area = (
                        career_area.text.strip()
                        if career_area else ""
                    )

                    keywords = [
                        business,
                        job_type,
                        career_area
                    ]

                    keywords = [
                        k for k in keywords if k
                    ]

                    job_data = {
                        "company": COMPANY_NAME,
                        "title": title or "Not Mentioned",
                        "location": location or "India",
                        "apply_link": apply_link,
                        "logo": COMPANY_LOGO,
                        "keywords": list(set(keywords))
                    }

                    all_jobs.append(job_data)

                    print("Saving:", title)

                    # ✅ SAVE USING SAME CURSOR
                    save_job(job_data, cur)

                except Exception as e:
                    print("Skipping card:", e)

            # =============================
            # PAGINATION
            # =============================

            try:

                next_button = driver.find_element(
                    By.CSS_SELECTOR,
                    "a[rel='next']"
                )

                driver.execute_script(
                    "arguments[0].scrollIntoView();",
                    next_button
                )

                time.sleep(1)

                driver.execute_script(
                    "arguments[0].click();",
                    next_button
                )

                page_number += 1
                page_count += 1

                if page_count >= MAX_PAGES:
                    print("Reached max page limit.")
                    break

                time.sleep(3)

            except:
                print("No more pages found.")
                break

        # ✅ COMMIT ONCE
        conn.commit()

    finally:

        cur.close()
        conn.close()

        driver.quit()

    return all_jobs


# =============================
# MAIN
# =============================

if __name__ == "__main__":

    jobs_data = scrape_nestle_jobs()

    print(
        f"\n✅ Total India Jobs Collected: {len(jobs_data)}"
    )

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

    print(f"📂 Saved to {OUTPUT_FILE}")