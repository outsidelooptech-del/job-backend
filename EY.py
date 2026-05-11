import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from save_job import save_job

BASE_PAGE_1 = "https://careers.ey.com/search/?createNewAlert=false&q=&optionsFacetsDD_customfield1=&optionsFacetsDD_country=IN&optionsFacetsDD_city="
BASE_PAGE_2 = "https://careers.ey.com/search/?q=&sortColumn=referencedate&sortDirection=desc&optionsFacetsDD_country=IN&startrow="

MAX_JOBS = 500
PAGE_SIZE = 25


def scrape_ey_jobs():

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=options)

    jobs = []
    seen_links = set()
    page_index = 0

    while len(jobs) < MAX_JOBS:

        # Build URL
        if page_index == 0:
            url = BASE_PAGE_1
        else:
            startrow = page_index * PAGE_SIZE
            url = BASE_PAGE_2 + str(startrow)

        print("Scraping:", url)

        driver.get(url)
        time.sleep(3)

        rows = driver.find_elements(By.CSS_SELECTOR, "tr.data-row")

        if not rows:
            break

        for row in rows:

            if len(jobs) >= MAX_JOBS:
                break

            try:
                title_element = row.find_element(By.CSS_SELECTOR, "a.jobTitle-link")

                title = title_element.text.strip()
                href = title_element.get_attribute("href")

                if href.startswith("http"):
                    apply_link = href
                else:
                    apply_link = "https://careers.ey.com" + href

                if apply_link in seen_links:
                    continue

                seen_links.add(apply_link)

                # Location extraction
                try:
                    location = row.find_element(
                        By.CSS_SELECTOR,
                        "span.jobLocation"
                    ).text.strip()
                except Exception:
                    location = ""

                job_data = {
                    "company": "EY",
                    "job_title": title,
                    "location": location,
                    "apply_link": apply_link,
                    "keywords": [location]
                }

                jobs.append(job_data)
                save_job(job_data)

            except Exception:
                continue

        print("Collected jobs:", len(jobs))

        page_index += 1

        # Safety break
        if page_index > 40:
            break

    driver.quit()
    return jobs


# MAIN
if __name__ == "__main__":

    jobs = scrape_ey_jobs()

    print("\nTotal Jobs Scraped:", len(jobs))

    with open("ey_jobs.json", "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=4, ensure_ascii=False)

    print("✅ Saved to ey_jobs.json")