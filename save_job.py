import re


# =============================
# CONFIG
# =============================

LOGO_DEV_TOKEN = "pk_ak69YmTsSK6Yhcs1Its-RA"


# =============================
# HELPERS
# =============================

def clean_text(value):
    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


def truncate_text(value, max_length=5000):
    if not value:
        return value

    return str(value)[:max_length]


def clean_keywords(keywords):
    if not keywords:
        return []

    cleaned = []

    for keyword in keywords:
        if not keyword:
            continue

        keyword = str(keyword).strip()

        if keyword and keyword not in cleaned:
            cleaned.append(keyword)

    return cleaned


def normalize_apply_link(link):
    if not link:
        return None

    link = str(link).strip()

    if link.endswith("/"):
        link = link[:-1]

    return link


def normalize_posted_at(value):
    if not value:
        return None

    value = str(value).strip()

    # Accept only date/timestamp-like values:
    # 2026-05-11
    # 2026-05-11T10:30:00Z
    if re.match(r"^\d{4}-\d{2}-\d{2}", value):
        return value

    # Ignore values like:
    # Posted 30+ Days Ago, Today, Yesterday, 2 days ago
    return None


def slugify(text):
    if not text:
        return None

    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)

    return text.strip("-")


# =============================
# DETECTORS
# =============================

def detect_work_mode(location):
    if not location:
        return "Onsite"

    text = location.lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_job_type(title, keywords=None):
    text = (title or "").lower()
    kw = " ".join(keywords or []).lower()

    if "intern" in text or "intern" in kw:
        return "Internship"

    if "contract" in text or "contract" in kw:
        return "Contract"

    if "part time" in text or "part-time" in text:
        return "Part Time"

    return "Full Time"


def detect_experience(title, keywords=None):
    text = ((title or "") + " " + " ".join(keywords or [])).lower()

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
        or "staff" in text
        or "architect" in text
        or "principal" in text
        or "director" in text
    ):
        return "5+ yrs"

    return "Not specified"


def detect_category(title, skills=None, department=None):
    text = f"{title or ''} {skills or ''} {department or ''}".lower()

    if any(x in text for x in ["sap", "ui5", "fiori", "abap", "bpa"]):
        return "SAP"

    if any(x in text for x in ["data", "analyst", "analytics", "sql", "power bi", "tableau"]):
        return "Data Analytics"

    if any(x in text for x in ["machine learning", " ai ", " ml ", "deep learning", "nlp", "computer vision"]):
        return "AI/ML"

    if any(x in text for x in ["android", "kotlin", "ios", "swift", "mobile"]):
        return "Mobile Development"

    if any(x in text for x in ["frontend", "front end", "react", "angular", "javascript", "typescript", "ui developer"]):
        return "Frontend Development"

    if any(x in text for x in ["backend", "back end", "node", "java", "spring boot", "api", "microservices"]):
        return "Backend Development"

    if any(x in text for x in ["cloud", "aws", "azure", "gcp", "devops", "docker", "kubernetes"]):
        return "Cloud / DevOps"

    if any(x in text for x in ["qa", "test", "tester", "testing", "automation"]):
        return "Testing / QA"

    if any(x in text for x in ["business analyst", "product", "operations", "sales", "marketing"]):
        return "Business / Operations"

    if any(x in text for x in ["security", "cyber", "soc", "siem"]):
        return "Cybersecurity"

    return "General"


def detect_source_priority(source):
    source = (source or "").lower()

    if "api" in source:
        return 10

    if "workday" in source:
        return 9

    if "lever" in source or "greenhouse" in source:
        return 8

    if "careers" in source:
        return 7

    return 5


# =============================
# LOGO
# =============================

def get_logo(company):
    if not company:
        return None

    custom_domains = {
        "Accenture": "accenture.com",
        "Adobe": "adobe.com",
        "TCS": "tcs.com",
        "PwC": "pwc.com",
        "SAP": "sap.com",
        "Zoho": "zoho.com",
        "Uber": "uber.com",
        "Visa": "visa.com",
        "Walmart": "walmart.com",
        "PepsiCo": "pepsico.com",
        "Pfizer": "pfizer.com",
        "Philips": "philips.com",
        "Qualcomm": "qualcomm.com",
        "Razorpay": "razorpay.com",
        "Samsung": "samsung.com",
        "Siemens": "siemens.com",
        "Stripe": "stripe.com",
        "Synopsys": "synopsys.com",
        "Tech Mahindra": "techmahindra.com"
    }

    domain = custom_domains.get(company)

    if not domain:
        domain = company.lower().replace(" ", "").replace("&", "") + ".com"

    return f"https://img.logo.dev/{domain}?token={LOGO_DEV_TOKEN}"


# =============================
# SAVE JOB
# =============================

def save_job(job_data, cur):
    try:
        company = clean_text(job_data.get("company"))

        title = clean_text(
            job_data.get("title")
            or job_data.get("job_title")
        )

        location = clean_text(job_data.get("location")) or "Not Mentioned"

        apply_link = normalize_apply_link(
            clean_text(job_data.get("apply_link"))
        )

        if not company or not title or not apply_link:
            return

        keywords = clean_keywords(job_data.get("keywords"))
        skills = ", ".join(keywords) if keywords else None

        job_description = truncate_text(
            clean_text(job_data.get("job_description")) or "",
            15000
        )

        company_description = truncate_text(
            clean_text(job_data.get("company_description")),
            5000
        )

        work_mode = clean_text(job_data.get("work_mode")) or detect_work_mode(location)

        job_type = clean_text(job_data.get("job_type")) or detect_job_type(
            title,
            keywords
        )

        experience = clean_text(job_data.get("experience")) or detect_experience(
            title,
            keywords
        )

        salary = clean_text(job_data.get("salary")) or "Not disclosed"
        education = clean_text(job_data.get("education")) or "Not specified"

        department = (
            clean_text(job_data.get("department"))
            or (keywords[0] if keywords else "Not specified")
        )

        source = clean_text(job_data.get("source")) or company

        company_logo = (
            clean_text(job_data.get("company_logo"))
            or get_logo(company)
        )

        posted_at = normalize_posted_at(job_data.get("posted_at"))

        company_slug = (
            clean_text(job_data.get("company_slug"))
            or slugify(company)
        )

        job_slug = (
            clean_text(job_data.get("job_slug"))
            or slugify(f"{title}-{company}-{location}")
        )

        category = (
            clean_text(job_data.get("category"))
            or detect_category(title, skills, department)
        )

        source_priority = (
            job_data.get("source_priority")
            or detect_source_priority(source)
        )

        cur.execute(
            """
            INSERT INTO jobs
            (
                title,
                company,
                location,
                work_mode,
                job_type,
                company_description,
                job_description,
                skills,
                apply_link,
                source,
                company_logo,
                salary,
                experience,
                education,
                department,
                posted_at,
                company_slug,
                job_slug,
                category,
                source_priority,
                is_active
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true
            )
            ON CONFLICT (apply_link)
            DO UPDATE SET
                title = EXCLUDED.title,
                company = EXCLUDED.company,
                location = EXCLUDED.location,
                work_mode = EXCLUDED.work_mode,
                job_type = EXCLUDED.job_type,
                company_description = EXCLUDED.company_description,
                job_description = EXCLUDED.job_description,
                skills = EXCLUDED.skills,
                source = EXCLUDED.source,
                company_logo = EXCLUDED.company_logo,
                salary = EXCLUDED.salary,
                experience = EXCLUDED.experience,
                education = EXCLUDED.education,
                department = EXCLUDED.department,
                posted_at = EXCLUDED.posted_at,
                company_slug = EXCLUDED.company_slug,
                job_slug = EXCLUDED.job_slug,
                category = EXCLUDED.category,
                source_priority = EXCLUDED.source_priority,
                updated_at = NOW(),
                is_active = true
            """,
            (
                title,
                company,
                location,
                work_mode,
                job_type,
                company_description,
                job_description,
                skills,
                apply_link,
                source,
                company_logo,
                salary,
                experience,
                education,
                department,
                posted_at,
                company_slug,
                job_slug,
                category,
                source_priority
            )
        )

    except Exception as e:
        try:
            cur.connection.rollback()
        except Exception:
            pass

        print(
            f"❌ Failed saving job: "
            f"{job_data.get('title') or job_data.get('job_title')} | Error: {e}"
        )
