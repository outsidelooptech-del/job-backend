import asyncio
import json
from playwright.async_api import async_playwright
from database import get_connection
from save_job import save_job


COMPANY_NAME = "Boston Consulting Group"
COMPANY_LOGO = "https://img.logo.dev/bcg.com?token=pk_ak69YmTsSK6Yhcs1Its-RA"

BASE_URL = "https://careers.bcg.com"
SEARCH_URL = "https://careers.bcg.com/global/en/search-results?s=1"
OUTPUT_FILE = "bcg_india_jobs.json"


def detect_work_mode(location):
    if not location:
        return "Onsite"

    text = location.lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title):
    if not title:
        return "Full Time"

    text = title.lower()

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

    if "associate" in text or "analyst" in text:
        return "0-2 yrs"

    if "consultant" in text:
        return "2+ yrs"

    if "senior" in text or "manager" in text or "lead" in text or "principal" in text:
        return "5+ yrs"

    if "graduate" in text or "fresher" in text or "entry level" in text:
        return "Freshers"

    return "Not specified"


async def fetch_bcg_india_jobs():

    all_jobs = []
    seen_links = set()

    conn = get_connection()
    cur = conn.cursor()

    print(f"Started fetching {COMPANY_NAME} India jobs...")

    try:
        async with async_playwright() as p:

            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                for page_num in range(0, 15):

                    offset = page_num * 10

                    url = SEARCH_URL if offset == 0 else (
                        f"https://careers.bcg.com/global/en/search-results?from={offset}&s=1"
                    )

                    print(f"\nScraping page {page_num + 1}")

                    await page.goto(url, timeout=60000)
                    await page.wait_for_timeout(4000)

                    cards = await page.query_selector_all("div.information")

                    if not cards:
                        print("No more jobs — stopping.")
                        break

                    new_found = 0

                    for card in cards:

                        try:
                            title_el = await card.query_selector(".job-title span")
                            link_el = await card.query_selector(
                                "a[data-ph-at-id='job-link']"
                            )

                            if not title_el or not link_el:
                                continue

                            title = (await title_el.inner_text()).strip()

                            link = await link_el.get_attribute("href") or ""

                            location = await link_el.get_attribute(
                                "data-ph-at-job-location-text"
                            ) or ""

                            if not link:
                                continue

                            if link.startswith("/"):
                                apply_link = BASE_URL + link
                            else:
                                apply_link = link

                            if "india" not in location.lower():
                                continue

                            if apply_link in seen_links:
                                continue

                            seen_links.add(apply_link)
                            new_found += 1

                            department = None

                            try:
                                dept_el = await card.query_selector(
                                    "[data-ph-at-id='job-category-text'], .job-category"
                                )

                                if dept_el:
                                    department = (await dept_el.inner_text()).strip()

                            except Exception:
                                department = None

                            keywords = []

                            if department:
                                keywords.append(department)

                            job_data = {
                                "company": COMPANY_NAME,
                                "title": title or "Not Mentioned",
                                "location": location.strip() or "India",
                                "apply_link": apply_link,
                                "keywords": list(set(keywords)),

                                "source": "BCG Careers",
                                "company_logo": COMPANY_LOGO,
                                "work_mode": detect_work_mode(location),
                                "job_type": detect_job_type(title),
                                "experience": detect_experience(title),
                                "education": "Not specified",
                                "department": department,
                                "salary": "Not disclosed",
                                "job_description": "",
                                "company_description": "Boston Consulting Group is a global management consulting firm helping organizations with strategy, transformation, technology and operations.",
                                "posted_at": None
                            }

                            all_jobs.append(job_data)

                            print("Saving:", title)

                            save_job(job_data, cur)

                        except Exception as e:
                            print("Skipping job due to error:", e)
                            continue

                    if new_found == 0:
                        break

            finally:
                await browser.close()

        conn.commit()

        print(f"Finished saving {COMPANY_NAME} jobs to database.")

    except Exception as e:
        conn.rollback()
        print("Fatal error:", e)

    finally:
        cur.close()
        conn.close()

    return all_jobs


if __name__ == "__main__":

    jobs = asyncio.run(fetch_bcg_india_jobs())

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

    print(f"\n✅ Scraped {len(jobs)} {COMPANY_NAME} India jobs!")