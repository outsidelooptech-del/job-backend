import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from save_job import save_job

# ----------------------------
# CONFIG
# ----------------------------

BASE_URL = "https://www.mckinsey.com"
SEARCH_URL = "https://www.mckinsey.com/careers/search-jobs?countries=India&start="

MAX_START = 100
STEP = 20


# ----------------------------
# SCRAPER
# ----------------------------

def scrape_mckinsey_jobs():

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    all_jobs = []
    start = 0

    while start <= MAX_START:

        print(f"\nOpening page starting at {start}")

        driver.get(SEARCH_URL + str(start))

        wait = WebDriverWait(driver, 20)

        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//li[contains(@class,'job-listing')]")
                )
            )
        except:
            print("No more jobs found.")
            break

        time.sleep(3)

        job_cards = driver.find_elements(
            By.XPATH,
            "//li[contains(@class,'job-listing')]"
        )

        print("Jobs found on this page:", len(job_cards))

        if len(job_cards) == 0:
            break

        for job in job_cards:

            try:
                title_element = job.find_element(By.XPATH, ".//h2//a")
                title = title_element.text.strip().replace("Job title", "").strip()
                link = title_element.get_attribute("href")

                interest = job.find_element(
                    By.XPATH,
                    ".//p[contains(@class,'interests')]"
                ).text.replace("Job interest", "").strip()

                city = job.find_element(
                    By.XPATH,
                    ".//div[contains(@class,'city')]"
                ).text

                city = city.replace("List of cities where this job is available", "")
                city = city.replace("This job is available in", "").strip()

                job_data = {
                    "company": "McKinsey",
                    "job_title": title,
                    "location": city,
                    "apply_link": link,
                    "keywords": [
                        interest
                    ]
                }

                job_data["keywords"] = [k for k in job_data["keywords"] if k]

                all_jobs.append(job_data)
                save_job(job_data)   # ✅ fixed indentation (4 spaces)

            except:
                continue

        start += STEP
        time.sleep(2)

    driver.quit()

    return all_jobs


# ----------------------------
# MAIN
# ----------------------------

if __name__ == "__main__":

    print("🚀 McKinsey Job Scraper Started...\n")

    jobs_data = scrape_mckinsey_jobs()

    print("\n✅ Total Jobs Collected:", len(jobs_data))

    with open("mckinsey_jobs_india.json", "w", encoding="utf-8") as f:
        json.dump(jobs_data, f, indent=4, ensure_ascii=False)

    print("📂 Saved to mckinsey_jobs_india.json")