import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from save_job import save_job

# ----------------------------
# CONFIG
# ----------------------------

BASE_URL = "https://www.google.com/about/careers/applications/jobs/results?location=India"
PAGES_TO_SCRAPE = 3


# ----------------------------
# SCRAPER
# ----------------------------

def scrape_google_jobs():

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--log-level=3")
    # options.add_argument("--headless")

    driver = webdriver.Chrome(options=options)

    all_jobs = []

    for page in range(1, PAGES_TO_SCRAPE + 1):

        print(f"\nScraping Page {page}...")

        driver.get(f"{BASE_URL}&page={page}")
        time.sleep(5)

        # Scroll for lazy loading
        for _ in range(6):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        cards = driver.find_elements(By.CSS_SELECTOR, "li.lLd3Je")
        print("Total job cards found:", len(cards))

        for card in cards:

            try:
                title = card.find_element(By.CSS_SELECTOR, "h3.QJPWVe").text.strip()

                link = card.find_element(By.CSS_SELECTOR, "a.WpHeLc").get_attribute("href")

                # Location
                location = ""
                try:
                    location = card.find_element(By.CSS_SELECTOR, "span.r0wTof").text.strip()
                except:
                    pass

                # Experience Level
                experience = ""
                try:
                    experience = card.find_element(By.CSS_SELECTOR, "span.wVSTAb").text.strip()
                except:
                    pass

                job_data = {
                    "company": "Google",
                    "job_title": title,
                    "location": location,
                    "apply_link": link,
                    "keywords": [
                        experience
                    ]
                }

                # Remove empty keywords
                job_data["keywords"] = [k for k in job_data["keywords"] if k]

                all_jobs.append(job_data)
                save_job(job_data)

            except Exception:
                continue

    driver.quit()

    return all_jobs


# ----------------------------
# MAIN
# ----------------------------

if __name__ == "__main__":

    print("\n🚀 Google Jobs Scraper Started...\n")

    jobs_data = scrape_google_jobs()

    print("\n✅ Total Jobs Scraped:", len(jobs_data))

    # Save JSON
    with open("google_jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs_data, f, indent=4, ensure_ascii=False)

    print("\n📂 Saved Successfully: google_jobs.json")