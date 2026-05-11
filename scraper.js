require("dotenv").config();

const fetch = require("node-fetch");
const { Pool } = require("pg");

// ======================
// POSTGRES CONNECTION
// ======================

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

const LOGO_DEV_TOKEN = process.env.LOGO_DEV_TOKEN;

// ======================
// LEVER COMPANIES
// ======================

const leverCompanies = [
  "spotify",
  "scaleai",
  "asana",
  "databricks",
  "duolingo",
  "reddit",
  "twitch",
  "zapier",
  "clearbit",
  "udemy",
  "paytm",
  "meesho",
  "jiostar",
  "mindtickle",
  "lenskart",
  "cred",
  "highlevel",
  "titans",
  "dnb",
  "viacom18",
  "inmobi",
  "hackerrank",
  "aftershoot",
  "wingassistant",
  "tripleseat",
  "remote",
  "engine",
  "wppmedia"
];

// ======================
// GREENHOUSE COMPANIES
// ======================

const greenhouseCompanies = [
  "airbnb",
  "stripe",
  "robinhood",
  "discord",
  "mongodb",
  "hubspot",
  "grammarly",
  "canva",
  "brex",
  "affirm",
  "ey",
  "agoda",
  "capco",
  "zscaler",
  "nice",
  "speechify",
  "bcg",
  "okta",
  "wpp",
  "gitlab",
  "roku",
  "turing",
  "smartsheet",
  "five9",
  "databricks",
  "altruist",
  "purestorage",
  "inovalon",
  "payoneer",
  "fivetran",
  "kaseya",
  "phonepe",
  "tide",
  "sonicwall",
  "razorpay",
  "myntra",
  "highradius",
  "appian",
  "zoominfo",
  "ghx",
  "cloudflare",
  "toast",
  "vonage",
  "anaplan"
];

// ======================
// COMPANY NAMES
// ======================

const companyNames = {
  scaleai: "Scale AI",
  jiostar: "JioStar",
  mindtickle: "Mindtickle",
  highlevel: "HighLevel",
  dnb: "Dun & Bradstreet",
  viacom18: "Viacom18",
  inmobi: "InMobi",
  hackerrank: "HackerRank",
  aftershoot: "Aftershoot",
  wingassistant: "Wing Assistant",
  wppmedia: "WPP Media",
  ey: "EY",
  bcg: "BCG",
  okta: "Okta",
  wpp: "WPP",
  gitlab: "GitLab",
  phonepe: "PhonePe",
  highradius: "HighRadius",
  ghx: "GHX"
};

// ======================
// COMPANY DOMAINS
// ======================

const companyDomains = {
  spotify: "spotify.com",
  scaleai: "scale.com",
  asana: "asana.com",
  databricks: "databricks.com",
  duolingo: "duolingo.com",
  reddit: "reddit.com",
  twitch: "twitch.tv",
  zapier: "zapier.com",
  clearbit: "clearbit.com",
  udemy: "udemy.com",
  paytm: "paytm.com",
  meesho: "meesho.com",
  lenskart: "lenskart.com",
  cred: "cred.club",
  inmobi: "inmobi.com",
  hackerrank: "hackerrank.com",
  airbnb: "airbnb.com",
  stripe: "stripe.com",
  robinhood: "robinhood.com",
  discord: "discord.com",
  mongodb: "mongodb.com",
  hubspot: "hubspot.com",
  grammarly: "grammarly.com",
  canva: "canva.com",
  brex: "brex.com",
  affirm: "affirm.com",
  ey: "ey.com",
  agoda: "agoda.com",
  capco: "capco.com",
  zscaler: "zscaler.com",
  okta: "okta.com",
  gitlab: "gitlab.com",
  phonepe: "phonepe.com",
  razorpay: "razorpay.com",
  myntra: "myntra.com",
  cloudflare: "cloudflare.com"
};

// ======================
// MAIN SCRAPER
// ======================

async function runScraper() {
  try {
    console.log("🚀 STARTING JOB PORTAL SCRAPER\n");

    await markOldJobsInactive();

    for (const company of leverCompanies) {
      await scrapeLeverCompany(company);
    }

    for (const company of greenhouseCompanies) {
      await scrapeGreenhouseCompany(company);
    }

    console.log("\n🎉 SCRAPING FINISHED");
  } catch (err) {
    console.error("❌ Fatal Error:", err.message);
  } finally {
    await pool.end();
  }
}

// ======================
// LEVER SCRAPER
// ======================

async function scrapeLeverCompany(company) {
  try {
    console.log(`🔵 Lever: ${company}`);

    const res = await fetchWithRetry(
      `https://api.lever.co/v0/postings/${company}?mode=json`
    );

    if (!res || !res.ok) {
      console.log(`❌ Failed: ${company}`);
      return;
    }

    const jobs = await res.json();

    for (const job of jobs) {
      const jobDescription = buildLeverDescription(job);
      const companyName = getCompanyName(company);

      await saveJob({
        title: job.text || "Untitled Role",
        company: companyName,
        location: cleanText(job.categories?.location) || "Remote",
        work_mode:
          cleanText(job.workplaceType) ||
          cleanText(job.categories?.workplaceType) ||
          detectWorkMode(job.categories?.location),

        job_type:
          cleanText(job.categories?.commitment) ||
          detectJobType(job.text),

        company_description: getCompanyDescription(companyName),
        job_description: jobDescription,
        skills: extractSkills(jobDescription),

        apply_link:
          normalizeApplyLink(job.hostedUrl) ||
          normalizeApplyLink(job.applyUrl),

        source: "Lever",
        company_logo: getCompanyLogo(company),

        salary: extractLeverSalary(job),
        experience:
          cleanText(job.categories?.level) ||
          detectExperience(`${job.text || ""} ${jobDescription || ""}`),

        education: detectEducation(jobDescription),

        department:
          cleanText(job.categories?.team) ||
          cleanText(job.categories?.department) ||
          "Not specified",

        posted_at:
          job.createdAt
            ? new Date(job.createdAt).toISOString()
            : null
      });
    }

    console.log(`✅ ${jobs.length} jobs from ${company}\n`);
  } catch (err) {
    console.log(`❌ Lever error (${company}):`, err.message);
  }
}

// ======================
// GREENHOUSE SCRAPER
// ======================

async function scrapeGreenhouseCompany(company) {
  try {
    console.log(`🟢 Greenhouse: ${company}`);

    const res = await fetchWithRetry(
      `https://boards-api.greenhouse.io/v1/boards/${company}/jobs?content=true`
    );

    if (!res || !res.ok) {
      console.log(`❌ Failed: ${company}`);
      return;
    }

    const data = await res.json();
    const jobs = data.jobs || [];

    for (const job of jobs) {
      const jobDescription = stripHtml(job.content || "");
      const companyName = getCompanyName(company);

      let workMode = null;

      if (job.metadata) {
        const wm = job.metadata.find(
          m => m.name && m.name.toLowerCase().includes("workplace")
        );

        if (wm) {
          workMode = cleanText(wm.value);
        }
      }

      await saveJob({
        title: job.title || "Untitled Role",
        company: companyName,
        location: cleanText(job.location?.name) || "Remote",

        work_mode:
          workMode ||
          detectWorkMode(job.location?.name),

        job_type: detectJobType(job.title),

        company_description: getCompanyDescription(companyName),
        job_description: jobDescription,
        skills: extractSkills(jobDescription),

        apply_link: normalizeApplyLink(job.absolute_url),

        source: "Greenhouse",
        company_logo: getCompanyLogo(company),

        salary: extractSalary(jobDescription),
        experience: detectExperience(`${job.title || ""} ${jobDescription || ""}`),
        education: detectEducation(jobDescription),

        department:
          cleanText(job.departments?.[0]?.name) ||
          "Not specified",

        posted_at: job.updated_at || null
      });
    }

    console.log(`✅ ${jobs.length} jobs from ${company}\n`);
  } catch (err) {
    console.log(`❌ Greenhouse error (${company}):`, err.message);
  }
}

// ======================
// SAVE JOB
// ======================

async function saveJob(job) {
  try {
    if (!job.apply_link || !job.title) {
      return;
    }

    await pool.query(
      `
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
        is_active
      )
      VALUES
      (
        $1,$2,$3,$4,$5,$6,$7,$8,$9,
        $10,$11,$12,$13,$14,$15,$16,true
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
        is_active = true
      `,
      [
        truncateText(job.title, 500),
        truncateText(job.company, 200),
        truncateText(job.location || "Not Mentioned", 500),
        job.work_mode || "Onsite",
        job.job_type || "Full Time",
        truncateText(job.company_description || "", 5000),
        truncateText(job.job_description || "", 15000),
        truncateText(job.skills || null, 3000),
        job.apply_link,
        job.source || job.company,
        job.company_logo || null,
        job.salary || "Not disclosed",
        job.experience || "Not specified",
        job.education || "Not specified",
        job.department || "Not specified",
        job.posted_at || null
      ]
    );

    console.log("✔", job.title);
  } catch (err) {
    console.log("❌ Insert error:", job.title, err.message);
  }
}

// ======================
// MARK OLD PORTAL JOBS INACTIVE
// ======================

async function markOldJobsInactive() {
  try {
    await pool.query(`
      UPDATE jobs
      SET is_active = false
      WHERE source IN ('Lever', 'Greenhouse')
    `);

    console.log("♻️ Old Lever/Greenhouse jobs marked inactive\n");
  } catch (err) {
    console.log("Inactive update error:", err.message);
  }
}

// ======================
// FETCH RETRY
// ======================

async function fetchWithRetry(url, options = {}, retries = 3) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 30000);

      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });

      clearTimeout(timeout);

      return response;
    } catch (err) {
      console.log(`Fetch attempt ${attempt} failed:`, err.message);

      if (attempt === retries) {
        return null;
      }

      await sleep(1000 * attempt);
    }
  }

  return null;
}

// ======================
// HELPERS
// ======================

function buildLeverDescription(job) {
  let description = "";

  if (job.descriptionPlain) {
    description += job.descriptionPlain + " ";
  }

  if (job.content?.description) {
    description += stripHtml(job.content.description) + " ";
  }

  if (job.content?.lists) {
    for (const list of job.content.lists) {
      description += " " + stripHtml(list.text || "") + " ";
      description += " " + stripHtml(list.content || "") + " ";
    }
  }

  return description.replace(/\s+/g, " ").trim();
}

function stripHtml(html) {
  if (!html) return "";

  return String(html)
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

function extractSkills(text) {
  if (!text) return null;

  const skills = [
    "Java",
    "Python",
    "JavaScript",
    "TypeScript",
    "React",
    "Node",
    "Node.js",
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "SQL",
    "MySQL",
    "PostgreSQL",
    "MongoDB",
    "Android",
    "Kotlin",
    "Swift",
    "C++",
    "C#",
    "Machine Learning",
    "AI",
    "TensorFlow",
    "PyTorch",
    "Firebase",
    "Spring Boot",
    "SAP",
    "UI5",
    "Fiori",
    "DevOps",
    "Linux",
    "Data Science",
    "Data Analytics"
  ];

  const lowerText = text.toLowerCase();

  const found = skills.filter(skill =>
    lowerText.includes(skill.toLowerCase())
  );

  return [...new Set(found)].join(", ") || null;
}

function detectWorkMode(text) {
  if (!text) return "Onsite";

  text = String(text).toLowerCase();

  if (text.includes("remote")) return "Remote";
  if (text.includes("hybrid")) return "Hybrid";

  return "Onsite";
}

function detectJobType(text) {
  if (!text) return "Full Time";

  text = String(text).toLowerCase();

  if (text.includes("intern")) return "Internship";
  if (text.includes("contract")) return "Contract";
  if (text.includes("part time") || text.includes("part-time")) return "Part Time";

  return "Full Time";
}

function detectExperience(text) {
  if (!text) return "Not specified";

  text = String(text).toLowerCase();

  if (text.includes("intern")) return "Internship";

  if (
    text.includes("fresher") ||
    text.includes("entry level") ||
    text.includes("graduate") ||
    text.includes("new grad")
  ) {
    return "Freshers";
  }

  if (
    text.includes("associate") ||
    text.includes("junior")
  ) {
    return "0-2 yrs";
  }

  if (
    text.includes("senior") ||
    text.includes("sr.")
  ) {
    return "3+ yrs";
  }

  if (
    text.includes("manager") ||
    text.includes("lead") ||
    text.includes("principal") ||
    text.includes("architect") ||
    text.includes("director") ||
    text.includes("staff")
  ) {
    return "5+ yrs";
  }

  return "Not specified";
}

function detectEducation(text) {
  if (!text) return "Not specified";

  text = String(text).toLowerCase();

  if (text.includes("b.tech") || text.includes("btech")) return "B.Tech";
  if (text.includes("b.e") || text.includes("be degree")) return "B.E";
  if (text.includes("bachelor")) return "Bachelor's Degree";
  if (text.includes("master")) return "Master's Degree";
  if (text.includes("mba")) return "MBA";
  if (text.includes("phd") || text.includes("ph.d")) return "PhD";

  return "Not specified";
}

function extractSalary(text) {
  if (!text) return "Not disclosed";

  const salaryRegex =
    /(?:₹|INR|\$|USD)\s?[\d,]+(?:\s?-\s?(?:₹|INR|\$|USD)?\s?[\d,]+)?/i;

  const match = String(text).match(salaryRegex);

  return match ? match[0] : "Not disclosed";
}

function extractLeverSalary(job) {
  if (job.salaryRange) {
    const min = job.salaryRange.min;
    const max = job.salaryRange.max;
    const currency = job.salaryRange.currency || "";

    if (min && max) {
      return `${currency} ${min} - ${max}`;
    }
  }

  if (job.salaryDescription) {
    return stripHtml(job.salaryDescription);
  }

  return "Not disclosed";
}

function getCompanyName(company) {
  return companyNames[company] || capitalize(company);
}

function getCompanyLogo(company) {
  const domain =
    companyDomains[company] ||
    `${company.replace(/\s+/g, "").toLowerCase()}.com`;

  return `https://img.logo.dev/${domain}?token=${LOGO_DEV_TOKEN}`;
}

function getCompanyDescription(company) {
  return `${company} is a leading company offering career opportunities across technology, product, operations, business, engineering, and support roles.`;
}

function cleanText(value) {
  if (value === undefined || value === null) return null;

  const text = String(value).trim();

  return text || null;
}

function truncateText(value, maxLength) {
  if (!value) return value;

  value = String(value);

  return value.length > maxLength
    ? value.substring(0, maxLength)
    : value;
}

function normalizeApplyLink(link) {
  if (!link) return null;

  link = String(link).trim();

  if (link.endsWith("/")) {
    link = link.slice(0, -1);
  }

  return link;
}

function capitalize(text) {
  if (!text) return "";

  return text
    .replace(/-/g, " ")
    .split(" ")
    .map(word =>
      word.charAt(0).toUpperCase() + word.slice(1)
    )
    .join(" ");
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ======================
// RUN
// ======================

runScraper();