import requests
import json
import time
import os

SOURCE_FILE = "internship_sources.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

# =====================================================
# LEVER CANDIDATES
# board = https://api.lever.co/v0/postings/{board}?mode=json
# =====================================================

LEVER_SOURCES = [
    {"company": "Meesho", "board": "meesho"},
    {"company": "CRED", "board": "cred"},
    {"company": "Postman", "board": "postman"},
    {"company": "Groww", "board": "groww"},
    {"company": "Navi", "board": "navi"},
    {"company": "Zeta", "board": "zeta"},
    {"company": "Swiggy", "board": "swiggy"},
    {"company": "Razorpay", "board": "razorpay"},
    {"company": "PhonePe", "board": "phonepe"},
    {"company": "Udaan", "board": "udaan"},
    {"company": "Dream11", "board": "dream11"},
    {"company": "MPL", "board": "mplgaming"},
    {"company": "Khatabook", "board": "khatabook"},
    {"company": "Upstox", "board": "upstox"},
    {"company": "Paytm", "board": "paytm"},
    {"company": "Slice", "board": "slice"},
    {"company": "Fi Money", "board": "epifi"},
    {"company": "Pocket FM", "board": "pocketfm"},
    {"company": "InVideo", "board": "invideo"},
    {"company": "Curefit", "board": "curefit"},
    {"company": "Dunzo", "board": "dunzo"},
    {"company": "Zepto", "board": "zepto"},
    {"company": "CoinSwitch", "board": "coinswitch"},
    {"company": "Unacademy", "board": "unacademy"},
    {"company": "ShareChat", "board": "sharechat"},
    {"company": "BrowserStack", "board": "browserstack"},
    {"company": "Urban Company", "board": "urbancompany"},
    {"company": "Ola", "board": "olacabs"},
    {"company": "Ola Electric", "board": "olaelectric"},
    {"company": "GoTo", "board": "goto"},
    {"company": "Gojek", "board": "gojek"},
    {"company": "Flipkart", "board": "flipkart"},
    {"company": "Mindtickle", "board": "mindtickle"},
    {"company": "Chargebee", "board": "chargebee"},
    {"company": "Freshworks", "board": "freshworks"},
    {"company": "Whatfix", "board": "whatfix"},
    {"company": "Observe AI", "board": "observeai"},
    {"company": "Plivo", "board": "plivo"},
    {"company": "Eightfold AI", "board": "eightfold"},
    {"company": "Innovaccer", "board": "innovaccer"},
    {"company": "BrowserStack", "board": "browserstackinc"},
    {"company": "Jar", "board": "jar"},
    {"company": "Jupiter", "board": "jupiter"},
    {"company": "FamPay", "board": "fampay"},
    {"company": "Scapia", "board": "scapia"},
    {"company": "Newton School", "board": "newtonschool"},
    {"company": "Supersourcing", "board": "supersourcing"},
    {"company": "Instawork", "board": "instawork"},
    {"company": "Turing", "board": "turing"},
    {"company": "Remote", "board": "remote"},
    {"company": "Tailscale", "board": "tailscale"},
    {"company": "Netlify", "board": "netlify"},
    {"company": "Zapier", "board": "zapier"},
    {"company": "Docker", "board": "docker"},
    {"company": "Toggl", "board": "toggl"},
    {"company": "Canonical", "board": "canonical"},
    {"company": "GitBook", "board": "gitbook"},
    {"company": "Sourcegraph", "board": "sourcegraph"},
    {"company": "PlanetScale", "board": "planetscale"},
    {"company": "Temporal", "board": "temporal"},
    {"company": "Astronomer", "board": "astronomer"},
    {"company": "Cohere", "board": "cohere"},
    {"company": "Runway", "board": "runway"},
    {"company": "Stability AI", "board": "stabilityai"},
    {"company": "Weights & Biases", "board": "wandb"},
    {"company": "Weights & Biases", "board": "weightsandbiases"},
    {"company": "Scale AI", "board": "scaleai"},
    {"company": "Anduril", "board": "anduril"},
    {"company": "Ramp", "board": "ramp"},
    {"company": "Mercury", "board": "mercury"},
    {"company": "Retool", "board": "retool"},
    {"company": "Vanta", "board": "vanta"},
    {"company": "Linear", "board": "linear"},
    {"company": "Watershed", "board": "watershed"},
    {"company": "Zip", "board": "zip"},
    {"company": "Faire", "board": "faire"},
    {"company": "Clipboard Health", "board": "clipboardhealth"},
    {"company": "Rippling", "board": "rippling"},
    {"company": "Deel", "board": "deel"},
    {"company": "Airwallex", "board": "airwallex"},
    {"company": "Wise", "board": "wise"},
    {"company": "Brex", "board": "brex"},
    {"company": "Plaid", "board": "plaid"},
    {"company": "Figma", "board": "figma"},
    {"company": "Notion", "board": "notion"},
    {"company": "Airtable", "board": "airtable"},
    {"company": "Amplitude", "board": "amplitude"},
    {"company": "Mixpanel", "board": "mixpanel"},
    {"company": "Segment", "board": "segment"},
    {"company": "Datadog", "board": "datadog"},
    {"company": "Snyk", "board": "snyk"},
    {"company": "HashiCorp", "board": "hashicorp"},
    {"company": "Elastic", "board": "elastic"},
    {"company": "MongoDB", "board": "mongodb"},
    {"company": "Confluent", "board": "confluent"},
    {"company": "Pure Storage", "board": "purestorage"},
    {"company": "Rubrik", "board": "rubrik"},
    {"company": "Cloudflare", "board": "cloudflare"},
    {"company": "Okta", "board": "okta"},
    {"company": "Box", "board": "box"},
    {"company": "Dropbox", "board": "dropbox"},
    {"company": "Asana", "board": "asana"},
    {"company": "Reddit", "board": "reddit"},
    {"company": "Discord", "board": "discord"},
    {"company": "Twitch", "board": "twitch"},
    {"company": "Duolingo", "board": "duolingo"}
]

# =====================================================
# SMARTRECRUITERS CANDIDATES
# board = https://api.smartrecruiters.com/v1/companies/{board}/postings
# =====================================================

SMARTRECRUITERS_SOURCES = [
    {"company": "Visa", "board": "Visa"},
    {"company": "Bosch", "board": "BoschGroup"},
    {"company": "Wolt", "board": "Wolt"},
    {"company": "Nagarro", "board": "Nagarro"},
    {"company": "Publicis Sapient", "board": "PublicisGroupe"},
    {"company": "Klarna", "board": "Klarna"},
    {"company": "Cognizant Softvision", "board": "CognizantSoftvision"},
    {"company": "Wise", "board": "Wise"},
    {"company": "HelloFresh", "board": "HelloFresh"},
    {"company": "Delivery Hero", "board": "DeliveryHero"},
    {"company": "Zalando", "board": "Zalando"},
    {"company": "Roche", "board": "Roche"},
    {"company": "Ubisoft", "board": "Ubisoft2"},
    {"company": "Eurofins", "board": "Eurofins"},
    {"company": "AUTO1 Group", "board": "AUTO1Group"},
    {"company": "TomTom", "board": "TomTom"},
    {"company": "Dynatrace", "board": "Dynatrace"},
    {"company": "N26", "board": "N26"},
    {"company": "Flix", "board": "Flix"},
    {"company": "Statkraft", "board": "Statkraft"},
    {"company": "Talan", "board": "Talan"},
    {"company": "Devoteam", "board": "Devoteam"},
    {"company": "InPost", "board": "InPost"},
    {"company": "Sportradar", "board": "Sportradar"},
    {"company": "Cint", "board": "Cint"},
    {"company": "NielsenIQ", "board": "NielsenIQ"},
    {"company": "Sopra Steria", "board": "SopraSteria"},
    {"company": "McFadyen Digital", "board": "McFadyenDigital"},
    {"company": "Sana Commerce", "board": "SanaCommerce"},
    {"company": "Mantu", "board": "Mantu"},
    {"company": "QIMA", "board": "QIMA"},
    {"company": "Accor", "board": "AccorCorpo"},
    {"company": "Colliers", "board": "Colliers"},
    {"company": "Turner & Townsend", "board": "TurnerTownsend"},
    {"company": "H&M", "board": "H&M"},
    {"company": "H&M Group", "board": "H&MGroup"},
    {"company": "Square", "board": "Square"},
    {"company": "Block", "board": "Block"},
    {"company": "Cash App", "board": "CashApp"},
    {"company": "Twitter", "board": "Twitter"},
    {"company": "X", "board": "X"},
    {"company": "Shopify", "board": "Shopify"},
    {"company": "Booking.com", "board": "Booking.com"},
    {"company": "Booking", "board": "Booking"},
    {"company": "Tripadvisor", "board": "Tripadvisor"},
    {"company": "Canva", "board": "Canva"},
    {"company": "Grab", "board": "Grab"},
    {"company": "Shopee", "board": "Shopee"},
    {"company": "Sea Group", "board": "SeaGroup"},
    {"company": "Thoughtworks", "board": "ThoughtWorks"},
    {"company": "Globant", "board": "Globant"},
    {"company": "Amdocs", "board": "Amdocs"},
    {"company": "MicroStrategy", "board": "MicroStrategy"},
    {"company": "Snowflake", "board": "Snowflake"},
    {"company": "Appian", "board": "Appian"},
    {"company": "Criteo", "board": "Criteo"},
    {"company": "Dataiku", "board": "Dataiku"},
    {"company": "Contentsquare", "board": "Contentsquare"},
    {"company": "Back Market", "board": "BackMarket"},
    {"company": "BlaBlaCar", "board": "BlaBlaCar"},
    {"company": "Ledger", "board": "Ledger"},
    {"company": "Qonto", "board": "Qonto"},
    {"company": "Malt", "board": "Malt"},
    {"company": "Doctolib", "board": "Doctolib"},
    {"company": "Alan", "board": "Alan"},
    {"company": "Voodoo", "board": "Voodoo"},
    {"company": "Gameloft", "board": "Gameloft"},
    {"company": "Mirakl", "board": "Mirakl"},
    {"company": "Spendesk", "board": "Spendesk"},
    {"company": "PayFit", "board": "PayFit"},
    {"company": "Aircall", "board": "Aircall"},
    {"company": "Deezer", "board": "Deezer"},
    {"company": "OVHcloud", "board": "OVHcloud"},
    {"company": "Amadeus", "board": "Amadeus"},
    {"company": "Capco", "board": "Capco"},
    {"company": "Publicis Media", "board": "PublicisMedia"},
    {"company": "Jellyfish", "board": "Jellyfish"},
    {"company": "King", "board": "King"},
    {"company": "Western Digital", "board": "WesternDigital"},
    {"company": "Renesas", "board": "Renesas"},
    {"company": "NXP", "board": "NXP"},
    {"company": "Arm", "board": "Arm"},
    {"company": "Checkout.com", "board": "Checkout.com"},
    {"company": "Adyen", "board": "Adyen"},
    {"company": "Mollie", "board": "Mollie"},
    {"company": "Bolt", "board": "Bolt"},
    {"company": "Revolut", "board": "Revolut"},
    {"company": "Monzo", "board": "Monzo"},
    {"company": "Starling Bank", "board": "StarlingBank"},
    {"company": "SumUp", "board": "SumUp"},
    {"company": "Trustly", "board": "Trustly"},
    {"company": "Tide", "board": "Tide"},
    {"company": "Personio", "board": "Personio"},
    {"company": "Celonis", "board": "Celonis"},
    {"company": "Miro", "board": "Miro"},
    {"company": "Typeform", "board": "Typeform"},
    {"company": "Remote", "board": "Remote"},
    {"company": "GitLab", "board": "GitLab"},
    {"company": "Canonical", "board": "Canonical"},
    {"company": "Red Hat", "board": "RedHat"},
    {"company": "Atos", "board": "Atos"},
    {"company": "SUSE", "board": "SUSE"},
    {"company": "Kyndryl", "board": "Kyndryl"}
]


def load_sources():
    if not os.path.exists(SOURCE_FILE):
        return []

    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_sources(sources):
    sources = remove_duplicate_sources(sources)

    with open(SOURCE_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2, ensure_ascii=False)


def remove_duplicate_sources(sources):
    unique = []
    seen = set()

    for source in sources:
        ats = str(source.get("ats", "")).strip().lower()
        board = str(source.get("board", "")).strip().lower()
        url = str(source.get("url", "")).strip().lower()

        key = f"{ats}:{url or board}"

        if key in seen:
            continue

        seen.add(key)
        unique.append(source)

    return unique


def already_exists(sources, ats, board):
    board = board.lower().strip()

    for source in sources:
        if (
            source.get("ats", "").lower() == ats.lower()
            and source.get("board", "").lower().strip() == board
        ):
            return True

    return False


def check_lever(board):
    url = f"https://api.lever.co/v0/postings/{board}?mode=json"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)

        if response.status_code != 200:
            return False, response.status_code, 0

        data = response.json()

        if not isinstance(data, list):
            return False, "INVALID_JSON", 0

        return True, 200, len(data)

    except Exception:
        return False, "ERROR", 0


def check_smartrecruiters(board):
    url = f"https://api.smartrecruiters.com/v1/companies/{board}/postings"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)

        if response.status_code != 200:
            return False, response.status_code, 0

        data = response.json()
        jobs = data.get("content", [])

        return True, 200, len(jobs)

    except Exception:
        return False, "ERROR", 0


def add_source(existing_sources, added_sources, company, ats, board, job_count):
    new_source = {
        "company": company,
        "ats": ats,
        "board": board
    }

    existing_sources.append(new_source)
    added_sources.append(new_source)

    print(f"✅ {ats.upper()} | {company} | {board} | Jobs: {job_count}")


def main():
    existing_sources = load_sources()
    added_sources = []

    print("🚀 Checking Lever sources...\n")

    for item in LEVER_SOURCES:
        company = item["company"]
        board = item["board"]

        if already_exists(existing_sources, "lever", board):
            print(f"⏭️ Lever already exists: {company}")
            continue

        ok, status, job_count = check_lever(board)

        if ok:
            add_source(existing_sources, added_sources, company, "lever", board, job_count)
        else:
            print(f"❌ Lever | {company} | {board} | Status: {status}")

        time.sleep(0.4)

    print("\n🚀 Checking SmartRecruiters sources...\n")

    for item in SMARTRECRUITERS_SOURCES:
        company = item["company"]
        board = item["board"]

        if already_exists(existing_sources, "smartrecruiters", board):
            print(f"⏭️ SmartRecruiters already exists: {company}")
            continue

        ok, status, job_count = check_smartrecruiters(board)

        if ok:
            add_source(existing_sources, added_sources, company, "smartrecruiters", board, job_count)
        else:
            print(f"❌ SmartRecruiters | {company} | {board} | Status: {status}")

        time.sleep(0.4)

    save_sources(existing_sources)

    print("\n🎯 New sources added:", len(added_sources))
    print("📂 Updated:", SOURCE_FILE)

    if added_sources:
        print("\n✅ Added sources:")
        for source in added_sources:
            print(source)


if __name__ == "__main__":
    main()