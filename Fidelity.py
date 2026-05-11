from playwright.sync_api import sync_playwright
import json

from save_job import save_job
from database import get_connection


COMPANY_NAME = "Fidelity"
COMPANY_LOGO = "https://img.logo.dev/fidelity.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://jobs.fidelity.com"
OUTPUT_FILE = "fidelity_jobs.json"


def detect_work_mode(location, work_pattern):
    text = f"{location or ''} {work_pattern or ''}".lower()

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

    if "graduate" in text or "fresher" in text or "entry level" in text:
        return "Freshers"

    if "associate" in text or "analyst" in text or "junior" in text:
        return "0-2 yrs"

    if "senior" in text or "sr." in text:
        return "3+ yrs"

    if (
        "manager" in text
        or "lead" in text
        or "director" in text
        or "principal" in text
    ):
        return "5+ yrs"

    return "Not specified"


def scrape_fidelity_jobs():

    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    print("🚀 Fidelity Job Scraper Started...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page_number = 1

            while True:
                url = f"{BASE_URL}/in/jobs/?page={page_number}&origin=global#results"

                print(f"Scraping page {page_number} → {url}")

                page.goto(url, timeout=60000)
                page.wait_for_timeout(4000)

                cards = page.query_selector_all("div.card.card-job")

                if not cards:
                    print("No more jobs found.")
                    break

                jobs_found = 0

                for card in cards:
                    try:
                        job_id = card.get_attribute("data-id")

                        title_elem = card.query_selector("h2.card-title")

                        if not title_elem:
                            continue

                        title = title_elem.inner_text().strip()

                        link_elem = title_elem.query_selector("a")

                        if not link_elem:
                            continue

                        link = link_elem.get_attribute("href")

                        if not link:
                            continue

                        apply_link = BASE_URL + link if link.startswith("/") else link

                        if apply_link in seen_links:
                            continue

                        seen_links.add(apply_link)

                        meta_items = card.query_selector_all("ul.job-meta li")

                        category = None
                        posted = None
                        location = "India"
                        work_pattern = None

                        try:
                            if len(meta_items) > 0:
                                spans = meta_items[0].query_selector_all("span")
                                category = spans[0].inner_text().strip() if len(spans) > 0 else None
                                posted = spans[1].inner_text().strip() if len(spans) > 1 else None

                            if len(meta_items) > 1:
                                location = meta_items[1].inner_text().strip()

                            if len(meta_items) > 2:
                                work_pattern = meta_items[2].inner_text().strip()

                        except Exception:
                            pass

                        keywords = [
                            job_id,
                            category,
                            posted,
                            work_pattern
                        ]

                        keywords = list(set([k for k in keywords if k]))

                        job_data = {
                            "company": COMPANY_NAME,
                            "title": title or "Not Mentioned",
                            "location": location or "India",
                            "apply_link": apply_link,
                            "keywords": keywords,

                            "source": "Fidelity Careers",
                            "company_logo": COMPANY_LOGO,
                            "work_mode": detect_work_mode(location, work_pattern),
                            "job_type": detect_job_type(title, category),
                            "experience": detect_experience(title),
                            "education": "Not specified",
                            "department": category,
                            "salary": "Not disclosed",
                            "job_description": "",
                            "company_description": "Fidelity is a global financial services company providing investment, retirement, wealth management and technology services.",
                            "posted_at": posted
                        }

                        all_jobs.append(job_data)

                        print("Saving:", title)

                        save_job(job_data, cur)

                        jobs_found += 1

                    except Exception as e:
                        print("Error parsing job:", e)

                print(f"Collected {len(cards)} jobs from page {page_number}")

                if jobs_found == 0:
                    print("No new jobs parsed. Stopping.")
                    break

                page_number += 1

            browser.close()

        conn.commit()

        print(f"\n✅ Saved {len(all_jobs)} Fidelity jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            all_jobs,
            f,
            indent=4,
            ensure_ascii=False
        )

    print("Done ✅")
    print("Total jobs scraped:", len(all_jobs))

    return all_jobs


if __name__ == "__main__":
    scrape_fidelity_jobs()