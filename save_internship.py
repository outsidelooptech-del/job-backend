import re


# =============================
# CONFIG
# =============================

LOGO_DEV_TOKEN = "pk_ak69YmTsSK6Yhcs1Its-RA"


# =============================
# BASIC HELPERS
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

    # Accept only date/timestamp-like values
    # Example: 2026-05-11 or 2026-05-11T10:30:00Z
    if re.match(r"^\d{4}-\d{2}-\d{2}", value):
        return value

    return None


def clean_keywords(keywords):
    if not keywords:
        return []

    cleaned = []

    for keyword in keywords:
        if keyword is None:
            continue

        keyword = str(keyword).strip()

        if keyword and keyword not in cleaned:
            cleaned.append(keyword)

    return cleaned


def slugify(text):
    if not text:
        return None

    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)

    return text.strip("-")


# =============================
# LOGO HELPERS
# =============================

def slugify_company_to_domain(company):
    if not company:
        return None

    custom_domains = {
        "PhonePe": "phonepe.com",
        "HighRadius": "highradius.com",
        "GitLab": "gitlab.com",
        "Cloudflare": "cloudflare.com",
        "Meesho": "meesho.com",
        "CRED": "cred.club",
        "HubSpot": "hubspot.com",
        "Stripe": "stripe.com",
        "Airbnb": "airbnb.com",
        "Discord": "discord.com",
        "Fivetran": "fivetran.com",
        "Databricks": "databricks.com",
        "Okta": "okta.com",
        "Zscaler": "zscaler.com",
        "Scale AI": "scale.com",
        "Reddit": "reddit.com",
        "Twitch": "twitch.tv",
        "Duolingo": "duolingo.com",
        "BrowserStack": "browserstack.com",
        "Zepto": "zepto.in",
        "CoinSwitch": "coinswitch.co",
        "Unacademy": "unacademy.com",
        "ShareChat": "sharechat.com",
        "Perplexity": "perplexity.ai",
        "ElevenLabs": "elevenlabs.io",
        "Anthropic": "anthropic.com",
        "Mercor": "mercor.com",
        "Linear": "linear.app",
        "Clay": "clay.com",
        "Vapi": "vapi.ai",
        "Decagon": "decagon.ai"
    }

    return custom_domains.get(
        company,
        company.lower().replace(" ", "").replace("&", "") + ".com"
    )


def get_logo(company):
    domain = slugify_company_to_domain(company)

    if not domain:
        return None

    return f"https://img.logo.dev/{domain}?token={LOGO_DEV_TOKEN}"


# =============================
# DETECTORS
# =============================

def detect_work_mode(location, title=""):
    text = f"{location or ''} {title or ''}".lower()

    if "remote" in text:
        return "Remote"

    if "hybrid" in text:
        return "Hybrid"

    return "Onsite"


def detect_internship_type(title, keywords=None):
    text = f"{title or ''} {' '.join(keywords or [])}".lower()

    if "summer" in text:
        return "Summer Internship"

    if "winter" in text:
        return "Winter Internship"

    if "trainee" in text:
        return "Trainee"

    if "apprentice" in text:
        return "Apprenticeship"

    if "co-op" in text:
        return "Co-op Internship"

    if "campus" in text:
        return "Campus Internship"

    if "new grad" in text or "graduate" in text:
        return "Graduate Internship"

    return "Internship"


def detect_batch(title, keywords=None):
    text = f"{title or ''} {' '.join(keywords or [])}".lower()

    if "2028" in text:
        return "2028"

    if "2027" in text:
        return "2027"

    if "2026" in text:
        return "2026"

    if "2025" in text:
        return "2025"

    if "2024" in text:
        return "2024"

    return "Not specified"


def detect_eligibility(title, description="", keywords=None):
    text = f"{title or ''} {description or ''} {' '.join(keywords or [])}".lower()

    if "b.tech" in text or "btech" in text:
        return "B.Tech"

    if "b.e" in text or "be degree" in text:
        return "B.E"

    if "bca" in text:
        return "BCA"

    if "b.sc" in text or "bsc" in text:
        return "B.Sc"

    if "mca" in text:
        return "MCA"

    if "mba" in text:
        return "MBA"

    if "bachelor" in text or "undergraduate" in text:
        return "Bachelor's Degree"

    if "master" in text or "postgraduate" in text:
        return "Master's Degree"

    if "student" in text:
        return "Students"

    return "Not specified"


def detect_stipend(description="", keywords=None):
    text = f"{description or ''} {' '.join(keywords or [])}"

    patterns = [
        r"₹\s?\d+[,\d]*(?:\s?-\s?₹?\s?\d+[,\d]*)?(?:\s?/month|\s?per month|\s?monthly)?",
        r"INR\s?\d+[,\d]*(?:\s?-\s?INR?\s?\d+[,\d]*)?(?:\s?/month|\s?per month|\s?monthly)?",
        r"\d+\s?k\s?(?:per month|/month|monthly)",
        r"\$[\d,]+(?:\s?-\s?\$[\d,]+)?(?:\s?/month|\s?per month|\s?monthly)?"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return match.group(0)

    return "Not disclosed"


def detect_category(title, skills=None, department=None, description=""):
    text = f" {title or ''} {skills or ''} {department or ''} {description or ''} ".lower()

    if any(x in text for x in [" software ", " backend ", " frontend ", " full stack ", " java ", " python ", " javascript ", " react ", " node "]):
        return "Software Development"

    if any(x in text for x in [" data ", " analytics ", " analyst ", " sql ", " tableau ", " power bi ", " data science "]):
        return "Data / Analytics"

    if any(x in text for x in [" machine learning ", " ai ", " artificial intelligence ", " deep learning ", " ml ", " nlp "]):
        return "AI/ML"

    if any(x in text for x in [" marketing ", " content ", " social media ", " growth ", " brand "]):
        return "Marketing"

    if any(x in text for x in [" sales ", " business development ", " revenue ", " partnerships "]):
        return "Sales / Business"

    if any(x in text for x in [" product ", " product management ", " product manager "]):
        return "Product"

    if any(x in text for x in [" design ", " ui ", " ux ", " graphic "]):
        return "Design"

    if any(x in text for x in [" hr ", " people ", " talent ", " recruiting ", " human resources "]):
        return "HR / People"

    if any(x in text for x in [" legal ", " policy ", " compliance "]):
        return "Legal / Compliance"

    if any(x in text for x in [" security ", " cybersecurity ", " grc ", " threat "]):
        return "Cybersecurity"

    if any(x in text for x in [" support ", " customer ", " operations ", " ops "]):
        return "Operations / Support"

    return "General"


def normalize_location(location):
    if not location:
        return "India"

    text = str(location).strip()

    if text.lower() in ["remote - global", "remote global", "global remote", "remote"]:
        return "Remote"

    return text


# =============================
# SAVE INTERNSHIP
# =============================

def save_internship(internship_data, cur):
    try:
        company = clean_text(internship_data.get("company"))

        title = clean_text(
            internship_data.get("title")
            or internship_data.get("job_title")
        )

        location = normalize_location(
            clean_text(internship_data.get("location")) or "India"
        )

        apply_link = normalize_apply_link(
            clean_text(internship_data.get("apply_link"))
        )

        if not company or not title or not apply_link:
            return

        keywords = clean_keywords(
            internship_data.get("keywords")
        )

        skills = clean_text(
            internship_data.get("skills")
        )

        if not skills and keywords:
            skills = ", ".join(keywords)

        internship_description = truncate_text(
            clean_text(internship_data.get("internship_description"))
            or clean_text(internship_data.get("job_description"))
            or "",
            15000
        )

        company_description = truncate_text(
            clean_text(internship_data.get("company_description")),
            5000
        )

        source = clean_text(
            internship_data.get("source")
        ) or company

        company_logo = (
            clean_text(internship_data.get("company_logo"))
            or get_logo(company)
        )

        work_mode = (
            clean_text(internship_data.get("work_mode"))
            or detect_work_mode(location, title)
        )

        internship_type = (
            clean_text(internship_data.get("internship_type"))
            or detect_internship_type(title, keywords)
        )

        stipend = (
            clean_text(internship_data.get("stipend"))
            or detect_stipend(internship_description, keywords)
            or "Not disclosed"
        )

        eligibility = (
            clean_text(internship_data.get("eligibility"))
            or detect_eligibility(title, internship_description, keywords)
        )

        batch = (
            clean_text(internship_data.get("batch"))
            or detect_batch(title, keywords)
        )

        department = (
            clean_text(internship_data.get("department"))
            or (keywords[0] if keywords else "Not specified")
        )

        category = (
            clean_text(internship_data.get("category"))
            or detect_category(title, skills, department, internship_description)
        )

        posted_at = normalize_posted_at(
            internship_data.get("posted_at")
        )

        cur.execute(
            """
            INSERT INTO internships
            (
                title,
                company,
                location,
                work_mode,
                internship_type,
                company_description,
                internship_description,
                skills,
                apply_link,
                source,
                company_logo,
                stipend,
                eligibility,
                batch,
                department,
                category,
                posted_at,
                is_active
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,true
            )
            ON CONFLICT (apply_link)
            DO UPDATE SET
                title = EXCLUDED.title,
                company = EXCLUDED.company,
                location = EXCLUDED.location,
                work_mode = EXCLUDED.work_mode,
                internship_type = EXCLUDED.internship_type,
                company_description = EXCLUDED.company_description,
                internship_description = EXCLUDED.internship_description,
                skills = EXCLUDED.skills,
                source = EXCLUDED.source,
                company_logo = EXCLUDED.company_logo,
                stipend = EXCLUDED.stipend,
                eligibility = EXCLUDED.eligibility,
                batch = EXCLUDED.batch,
                department = EXCLUDED.department,
                category = EXCLUDED.category,
                posted_at = EXCLUDED.posted_at,
                updated_at = NOW(),
                is_active = true
            """,
            (
                title,
                company,
                location,
                work_mode,
                internship_type,
                company_description,
                internship_description,
                skills,
                apply_link,
                source,
                company_logo,
                stipend,
                eligibility,
                batch,
                department,
                category,
                posted_at
            )
        )

    except Exception as e:
        try:
            cur.connection.rollback()
        except Exception:
            pass

        print(
            f"❌ Failed saving internship: "
            f"{internship_data.get('title') or internship_data.get('job_title')} | Error: {e}"
        )