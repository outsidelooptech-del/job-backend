import requests
import json
import time
import os

SOURCE_FILE = "internship_sources.json"

WORKDAY_SOURCES = [
    {"company": "BrowserStack", "board": "External", "url": "https://browserstack.wd3.myworkdayjobs.com/External"},
    {"company": "Samsung", "board": "Samsung_Careers", "url": "https://sec.wd3.myworkdayjobs.com/Samsung_Careers"},
    {"company": "Salesforce", "board": "External_Career_Site", "url": "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site"},
    {"company": "NVIDIA", "board": "NVIDIAExternalCareerSite", "url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"},
    {"company": "Dell", "board": "External", "url": "https://dell.wd1.myworkdayjobs.com/External"},
    {"company": "Intel", "board": "External", "url": "https://intel.wd1.myworkdayjobs.com/External"},
    {"company": "PayPal", "board": "jobs", "url": "https://paypal.wd1.myworkdayjobs.com/jobs"},
    {"company": "Mastercard", "board": "CorporateCareers", "url": "https://mastercard.wd1.myworkdayjobs.com/CorporateCareers"},
    {"company": "Boeing", "board": "EXTERNAL_CAREERS", "url": "https://boeing.wd1.myworkdayjobs.com/EXTERNAL_CAREERS"},
    {"company": "Motorola Solutions", "board": "Careers", "url": "https://motorolasolutions.wd5.myworkdayjobs.com/Careers"},
    {"company": "JLL", "board": "jllcareers", "url": "https://jll.wd1.myworkdayjobs.com/jllcareers"},

    {"company": "Adobe", "board": "external_experienced", "url": "https://adobe.wd5.myworkdayjobs.com/external_experienced"},
    {"company": "HP", "board": "ExternalCareerSite", "url": "https://hp.wd5.myworkdayjobs.com/ExternalCareerSite"},
    {"company": "HPE", "board": "Jobsathpe", "url": "https://hpe.wd5.myworkdayjobs.com/Jobsathpe"},
    {"company": "Lenovo", "board": "Lenovo", "url": "https://lenovo.wd5.myworkdayjobs.com/Lenovo"},
    {"company": "AMD", "board": "careers", "url": "https://amd.wd1.myworkdayjobs.com/careers"},
    {"company": "Micron", "board": "External", "url": "https://micron.wd1.myworkdayjobs.com/External"},
    {"company": "Analog Devices", "board": "External", "url": "https://analogdevices.wd1.myworkdayjobs.com/External"},
    {"company": "Marvell", "board": "MarvellCareers", "url": "https://marvell.wd1.myworkdayjobs.com/MarvellCareers"},
    {"company": "Western Digital", "board": "External", "url": "https://wdc.wd1.myworkdayjobs.com/External"},
    {"company": "Seagate", "board": "External", "url": "https://seagate.wd1.myworkdayjobs.com/External"},

    {"company": "Walmart Global Tech", "board": "WalmartExternal", "url": "https://walmart.wd5.myworkdayjobs.com/WalmartExternal"},
    {"company": "Target", "board": "targetcareers", "url": "https://target.wd5.myworkdayjobs.com/targetcareers"},
    {"company": "Lowe's", "board": "LWS_External_CS", "url": "https://lowes.wd5.myworkdayjobs.com/LWS_External_CS"},
    {"company": "Home Depot", "board": "homedepotcareers", "url": "https://homedepot.wd5.myworkdayjobs.com/homedepotcareers"},
    {"company": "Best Buy", "board": "BestBuy", "url": "https://bestbuy.wd5.myworkdayjobs.com/BestBuy"},
    {"company": "Nike", "board": "nike", "url": "https://nike.wd1.myworkdayjobs.com/nike"},
    {"company": "Adidas", "board": "adidas", "url": "https://adidas.wd3.myworkdayjobs.com/adidas"},
    {"company": "Lululemon", "board": "lululemon", "url": "https://lululemon.wd3.myworkdayjobs.com/lululemon"},
    {"company": "Levi Strauss", "board": "External", "url": "https://levistrauss.wd5.myworkdayjobs.com/External"},

    {"company": "Citi", "board": "Global", "url": "https://citi.wd5.myworkdayjobs.com/Global"},
    {"company": "BlackRock", "board": "BlackRock_Professional", "url": "https://blackrock.wd1.myworkdayjobs.com/BlackRock_Professional"},
    {"company": "Goldman Sachs", "board": "External", "url": "https://goldmansachs.wd1.myworkdayjobs.com/External"},
    {"company": "Morgan Stanley", "board": "External", "url": "https://morganstanley.wd5.myworkdayjobs.com/External"},
    {"company": "Bank of America", "board": "BankOfAmerica", "url": "https://bankofamerica.wd1.myworkdayjobs.com/BankOfAmerica"},
    {"company": "Visa", "board": "Jobs", "url": "https://visa.wd1.myworkdayjobs.com/Jobs"},
    {"company": "Fiserv", "board": "FiservCareers", "url": "https://fiserv.wd5.myworkdayjobs.com/FiservCareers"},
    {"company": "Fidelity", "board": "jobs", "url": "https://fidelity.wd1.myworkdayjobs.com/jobs"},
    {"company": "S&P Global", "board": "SPGlobal_Careers", "url": "https://spgi.wd5.myworkdayjobs.com/SPGlobal_Careers"},

    {"company": "Johnson Controls", "board": "External", "url": "https://johnsoncontrols.wd5.myworkdayjobs.com/External"},
    {"company": "Honeywell", "board": "ExternalCareerSite", "url": "https://honeywell.wd5.myworkdayjobs.com/ExternalCareerSite"},
    {"company": "GE Aerospace", "board": "External", "url": "https://geaerospace.wd5.myworkdayjobs.com/External"},
    {"company": "GE HealthCare", "board": "GEHC_External", "url": "https://gehealthcare.wd5.myworkdayjobs.com/GEHC_External"},
    {"company": "Carrier", "board": "External", "url": "https://carrier.wd5.myworkdayjobs.com/External"},
    {"company": "Otis", "board": "Otis", "url": "https://otis.wd5.myworkdayjobs.com/Otis"},
    {"company": "Caterpillar", "board": "Careers", "url": "https://cat.wd5.myworkdayjobs.com/Careers"},
    {"company": "3M", "board": "Search", "url": "https://3m.wd1.myworkdayjobs.com/Search"},
    {"company": "Emerson", "board": "External", "url": "https://emerson.wd5.myworkdayjobs.com/External"},
    {"company": "Eaton", "board": "EatonCareers", "url": "https://eaton.wd1.myworkdayjobs.com/EatonCareers"},
    {"company": "Schneider Electric", "board": "External", "url": "https://se.wd3.myworkdayjobs.com/External"},

    {"company": "Philips", "board": "JobsHub", "url": "https://philips.wd3.myworkdayjobs.com/JobsHub"},
    {"company": "Siemens Healthineers", "board": "Careers", "url": "https://siemens-healthineers.wd3.myworkdayjobs.com/Careers"},
    {"company": "Boston Scientific", "board": "Hybrid", "url": "https://bostonscientific.wd5.myworkdayjobs.com/Hybrid"},
    {"company": "Medtronic", "board": "MedtronicCareers", "url": "https://medtronic.wd1.myworkdayjobs.com/MedtronicCareers"},
    {"company": "Stryker", "board": "StrykerCareers", "url": "https://stryker.wd5.myworkdayjobs.com/StrykerCareers"},
    {"company": "Danaher", "board": "DanaherGlobal", "url": "https://danaher.wd1.myworkdayjobs.com/DanaherGlobal"},
    {"company": "Thermo Fisher", "board": "ThermoFisherExternal", "url": "https://thermofisher.wd5.myworkdayjobs.com/ThermoFisherExternal"},
    {"company": "IQVIA", "board": "IQVIA", "url": "https://iqvia.wd1.myworkdayjobs.com/IQVIA"},

    {"company": "Thomson Reuters", "board": "Careers", "url": "https://thomsonreuters.wd5.myworkdayjobs.com/Careers"},
    {"company": "RELX", "board": "LexisNexis", "url": "https://relx.wd3.myworkdayjobs.com/LexisNexis"},
    {"company": "Wolters Kluwer", "board": "External", "url": "https://wolterskluwer.wd3.myworkdayjobs.com/External"},
    {"company": "Pearson", "board": "PearsonCareers", "url": "https://pearson.wd3.myworkdayjobs.com/PearsonCareers"},
    {"company": "Elsevier", "board": "ElsevierJobs", "url": "https://elsevier.wd3.myworkdayjobs.com/ElsevierJobs"},

    {"company": "Hilton", "board": "HiltonJobs", "url": "https://hilton.wd1.myworkdayjobs.com/HiltonJobs"},
    {"company": "Marriott", "board": "marriott", "url": "https://marriott.wd5.myworkdayjobs.com/marriott"},
    {"company": "Hyatt", "board": "HyattJobs", "url": "https://hyatt.wd5.myworkdayjobs.com/HyattJobs"},
    {"company": "Expedia", "board": "Expedia_Group_Careers", "url": "https://expediagroup.wd5.myworkdayjobs.com/Expedia_Group_Careers"},
    {"company": "Booking Holdings", "board": "Booking", "url": "https://booking.wd3.myworkdayjobs.com/Booking"},

    {"company": "Uber", "board": "UberEats", "url": "https://uber.wd1.myworkdayjobs.com/UberEats"},
    {"company": "Lyft", "board": "Lyft", "url": "https://lyft.wd1.myworkdayjobs.com/Lyft"},
    {"company": "DoorDash", "board": "DoorDash", "url": "https://doordash.wd5.myworkdayjobs.com/DoorDash"},
    {"company": "Instacart", "board": "Instacart", "url": "https://instacart.wd5.myworkdayjobs.com/Instacart"},

    {"company": "Workday", "board": "Workday", "url": "https://workday.wd5.myworkdayjobs.com/Workday"},
    {"company": "Okta", "board": "Okta", "url": "https://okta.wd5.myworkdayjobs.com/Okta"},
    {"company": "Box", "board": "Box", "url": "https://box.wd1.myworkdayjobs.com/Box"},
    {"company": "DocuSign", "board": "External", "url": "https://docusign.wd1.myworkdayjobs.com/External"},
    {"company": "Splunk", "board": "SplunkExternalCareerSite", "url": "https://splunk.wd1.myworkdayjobs.com/SplunkExternalCareerSite"},
    {"company": "Zoom", "board": "Zoom", "url": "https://zoom.wd5.myworkdayjobs.com/Zoom"},
    {"company": "Atlassian", "board": "Atlassian", "url": "https://atlassian.wd5.myworkdayjobs.com/Atlassian"},
    {"company": "ServiceNow", "board": "External", "url": "https://servicenow.wd5.myworkdayjobs.com/External"},
    {"company": "VMware", "board": "VMwareCareers", "url": "https://vmware.wd1.myworkdayjobs.com/VMwareCareers"},

    {"company": "Unilever", "board": "Unilever_Experienced_Professionals", "url": "https://unilever.wd3.myworkdayjobs.com/Unilever_Experienced_Professionals"},
    {"company": "PepsiCo", "board": "PepsiCoJobs", "url": "https://pepsico.wd1.myworkdayjobs.com/PepsiCoJobs"},
    {"company": "Coca-Cola", "board": "coca-cola-careers", "url": "https://coca-cola.wd1.myworkdayjobs.com/coca-cola-careers"},
    {"company": "Mondelez", "board": "External", "url": "https://mdlz.wd5.myworkdayjobs.com/External"},
    {"company": "Mars", "board": "Mars", "url": "https://mars.wd5.myworkdayjobs.com/Mars"},
    {"company": "Nestle", "board": "NestleCareers", "url": "https://nestle.wd3.myworkdayjobs.com/NestleCareers"},

    {"company": "Ford", "board": "FordJobs", "url": "https://ford.wd1.myworkdayjobs.com/FordJobs"},
    {"company": "GM", "board": "Careers_GM", "url": "https://gm.wd5.myworkdayjobs.com/Careers_GM"},
    {"company": "Volvo", "board": "VolvoCars", "url": "https://volvocars.wd3.myworkdayjobs.com/VolvoCars"},
    {"company": "Rivian", "board": "Rivian", "url": "https://rivian.wd5.myworkdayjobs.com/Rivian"},
    {"company": "Tesla", "board": "TeslaExternal", "url": "https://tesla.wd5.myworkdayjobs.com/TeslaExternal"},

    {"company": "Accenture", "board": "AccentureCareers", "url": "https://accenture.wd3.myworkdayjobs.com/AccentureCareers"},
    {"company": "Cognizant", "board": "External", "url": "https://cognizant.wd5.myworkdayjobs.com/External"},
    {"company": "Capgemini", "board": "CapgeminiGlobal", "url": "https://capgemini.wd3.myworkdayjobs.com/CapgeminiGlobal"},
    {"company": "NTT DATA", "board": "NTTDATA", "url": "https://nttdata.wd3.myworkdayjobs.com/NTTDATA"},
    {"company": "DXC Technology", "board": "DXCJobs", "url": "https://dxc.wd1.myworkdayjobs.com/DXCJobs"},
    {"company": "EPAM", "board": "EPAM_Careers", "url": "https://epam.wd3.myworkdayjobs.com/EPAM_Careers"},
    {"company": "Thoughtworks", "board": "Careers", "url": "https://thoughtworks.wd5.myworkdayjobs.com/Careers"},

    {"company": "Roche", "board": "Roche-ext", "url": "https://roche.wd3.myworkdayjobs.com/Roche-ext"},
    {"company": "Novartis", "board": "Novartis_Careers", "url": "https://novartis.wd3.myworkdayjobs.com/Novartis_Careers"},
    {"company": "GSK", "board": "GSKCareers", "url": "https://gsk.wd5.myworkdayjobs.com/GSKCareers"},
    {"company": "AstraZeneca", "board": "Careers", "url": "https://astrazeneca.wd3.myworkdayjobs.com/Careers"},
    {"company": "Pfizer", "board": "PfizerCareers", "url": "https://pfizer.wd1.myworkdayjobs.com/PfizerCareers"}
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json"
}


def load_sources():
    if not os.path.exists(SOURCE_FILE):
        return []

    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_sources(sources):
    with open(SOURCE_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2, ensure_ascii=False)


def already_exists(sources, ats, url):
    for source in sources:
        if (
            source.get("ats", "").lower() == ats.lower()
            and source.get("url", "").rstrip("/") == url.rstrip("/")
        ):
            return True
    return False


def check_workday(source):
    base_url = source["url"].rstrip("/")
    api_url = base_url + "/jobs"

    payload = {
        "appliedFacets": {},
        "limit": 20,
        "offset": 0,
        "searchText": "intern"
    }

    try:
        response = requests.post(
            api_url,
            headers=HEADERS,
            json=payload,
            timeout=20
        )

        if response.status_code != 200:
            return False, response.status_code, 0

        try:
            data = response.json()
        except Exception:
            return False, "NON_JSON_RESPONSE", 0

        jobs = data.get("jobPostings", [])
        return True, 200, len(jobs)

    except Exception as e:
        print(f"⚠️ Error checking {source['company']}: {e}")
        return False, "ERROR", 0


def main():
    existing_sources = load_sources()
    added = []

    print("🚀 Checking Workday sources...\n")

    for source in WORKDAY_SOURCES:
        company = source["company"]
        url = source["url"]

        if already_exists(existing_sources, "workday", url):
            print(f"⏭️ Already exists: {company}")
            continue

        ok, status, job_count = check_workday(source)

        if ok:
            print(f"✅ {company} | Status: {status} | Intern search jobs: {job_count}")

            new_source = {
                "company": company,
                "ats": "workday",
                "board": source["board"],
                "url": source["url"]
            }

            existing_sources.append(new_source)
            added.append(new_source)
        else:
            print(f"❌ {company} | Status: {status}")

        time.sleep(0.7)

    save_sources(existing_sources)

    print("\n🎯 New Workday sources added:", len(added))
    print("📂 Updated:", SOURCE_FILE)

    if added:
        print("\n✅ Added:")
        for item in added:
            print(item)


if __name__ == "__main__":
    main()