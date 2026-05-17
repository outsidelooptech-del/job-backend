require("dotenv").config();

const fs = require("fs");
const fetch = require("node-fetch");
const { Pool } = require("pg");

const SOURCE_FILE = "job_sources.json";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

const LOGO_DEV_TOKEN = process.env.LOGO_DEV_TOKEN;

function loadJobSources() {
  return JSON.parse(fs.readFileSync(SOURCE_FILE, "utf8"));
}

async function runScraper() {
  try {
    console.log("🚀 STARTING JOB PORTAL SCRAPER\n");

    await markOldJobsInactive();

    const sources = loadJobSources();

    for (const source of sources) {
      if (source.enabled === false) continue;

      const ats = String(source.ats || "").toLowerCase();

      if (ats === "lever") {
        await scrapeLeverCompany(source);

      } else if (ats === "greenhouse") {
        await scrapeGreenhouseCompany(source);

      } else if (ats === "smartrecruiters") {
        await scrapeSmartRecruitersCompany(source);

      } else if (ats === "workday") {
        await scrapeWorkdayCompany(source);

      } else if (ats === "ashby") {
        await scrapeAshbyCompany(source);

      } else if (ats === "workable") {
        await scrapeWorkableCompany(source);

      } else if (ats === "icims") {
        await scrapeICIMSCompany(source);

      } else if (ats === "successfactors") {
        await scrapeSuccessFactorsCompany(source);

      } else {
        console.log("❌ Unsupported ATS:", source.ats, source.company);
      }

      await sleep(700);
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

async function scrapeLeverCompany(source) {
  try {
    const board = source.board;
    const companyName = source.company;

    console.log(`🔵 Lever: ${companyName}`);

    const res = await fetchWithRetry(
      `https://api.lever.co/v0/postings/${board}?mode=json`
    );

    if (!res || !res.ok) {
      console.log(`❌ Failed: ${companyName}`);
      return;
    }

    const jobs = await res.json();

    for (const job of jobs) {
      const jobDescription = buildLeverDescription(job);

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
        company_logo: getCompanyLogo(source),

        salary: extractLeverSalary(job),
        experience:
          cleanText(job.categories?.level) ||
          detectExperience(`${job.text || ""} ${jobDescription || ""}`),

        education: detectEducation(jobDescription),

        department:
          cleanText(job.categories?.team) ||
          cleanText(job.categories?.department) ||
          "Not specified",

        posted_at: job.createdAt ? new Date(job.createdAt).toISOString() : null
      });
    }

    console.log(`✅ ${jobs.length} jobs from ${companyName}\n`);
  } catch (err) {
    console.log(`❌ Lever error (${source.company}):`, err.message);
  }
}

// ======================
// GREENHOUSE SCRAPER
// ======================

async function scrapeGreenhouseCompany(source) {
  try {
    const board = source.board;
    const companyName = source.company;

    console.log(`🟢 Greenhouse: ${companyName}`);

    const url =
      source.url ||
      `https://boards-api.greenhouse.io/v1/boards/${board}/jobs?content=true`;

    const res = await fetchWithRetry(url);

    if (!res || !res.ok) {
      console.log(`❌ Failed: ${companyName}`);
      return;
    }

    const data = await res.json();
    const jobs = data.jobs || [];

    for (const job of jobs) {
      const jobDescription = stripHtml(job.content || "");

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
        company_logo: getCompanyLogo(source),

        salary: extractSalary(jobDescription),
        experience: detectExperience(`${job.title || ""} ${jobDescription || ""}`),
        education: detectEducation(jobDescription),

        department:
          cleanText(job.departments?.[0]?.name) ||
          "Not specified",

        posted_at: job.updated_at || null
      });
    }

    console.log(`✅ ${jobs.length} jobs from ${companyName}\n`);
  } catch (err) {
    console.log(`❌ Greenhouse error (${source.company}):`, err.message);
  }
}

// ======================
// SMARTRECRUITERS SCRAPER
// ======================

async function scrapeSmartRecruitersCompany(source) {
  try {
    const board = source.board;
    const companyName = source.company;

    console.log(`🟠 SmartRecruiters: ${companyName}`);

    const url =
      source.url ||
      `https://api.smartrecruiters.com/v1/companies/${board}/postings`;

    const res = await fetchWithRetry(url);

    if (!res || !res.ok) {
      console.log(`❌ Failed: ${companyName}`);
      return;
    }

    const data = await res.json();
    const jobs = data.content || [];

    for (const job of jobs) {
      const title = job.name || "Untitled Role";

      const location =
        job.location?.city ||
        job.location?.region ||
        job.location?.country ||
        "Remote";

      await saveJob({
        title,
        company: companyName,
        location,
        work_mode: detectWorkMode(location),
        job_type: detectJobType(title),
        company_description: getCompanyDescription(companyName),
        job_description: "",
        skills: null,
        apply_link: normalizeApplyLink(job.ref || job.applyUrl),
        source: "SmartRecruiters",
        company_logo: getCompanyLogo(source),
        salary: "Not disclosed",
        experience: detectExperience(title),
        education: "Not specified",
        department: job.department?.label || "Not specified",
        posted_at: job.releasedDate || null
      });
    }

    console.log(`✅ ${jobs.length} jobs from ${companyName}\n`);
  } catch (err) {
    console.log(`❌ SmartRecruiters error (${source.company}):`, err.message);
  }
}

// ======================
// WORKDAY SCRAPER
// ======================

async function scrapeWorkdayCompany(source) {
  try {
    const companyName = source.company;
    const baseUrl = source.url;

    if (!baseUrl) {
      console.log(`❌ Workday URL missing: ${companyName}`);
      return;
    }

    console.log(`🟤 Workday: ${companyName}`);

    const apiUrl = `${baseUrl.replace(/\/$/, "")}/jobs`;

    const res = await fetchWithRetry(apiUrl, {
      method: "POST",
      headers: {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        appliedFacets: {},
        limit: 100,
        offset: 0,
        searchText: ""
      })
    });

    if (!res || !res.ok) {
      console.log(`❌ Failed: ${companyName}`);
      return;
    }

    let data;

    try {
      data = await res.json();
    } catch {
      console.log(`❌ Non JSON Workday response: ${companyName}`);
      return;
    }

    const jobs = data.jobPostings || [];

    for (const job of jobs) {
      const title = job.title || "Untitled Role";
      const location = job.locationsText || "Remote";

      const applyLink = job.externalPath
        ? `${baseUrl.replace(/\/$/, "")}${job.externalPath}`
        : baseUrl;

      await saveJob({
        title,
        company: companyName,
        location,
        work_mode: detectWorkMode(location),
        job_type: detectJobType(title),
        company_description: getCompanyDescription(companyName),
        job_description: "",
        skills: null,
        apply_link: normalizeApplyLink(applyLink),
        source: "Workday",
        company_logo: getCompanyLogo(source),
        salary: "Not disclosed",
        experience: detectExperience(title),
        education: "Not specified",
        department: "Not specified",
        posted_at: job.postedOn || null
      });
    }

    console.log(`✅ ${jobs.length} jobs from ${companyName}\n`);
  } catch (err) {
    console.log(`❌ Workday error (${source.company}):`, err.message);
  }
}
// ======================
// ASHBY SCRAPER
// ======================

async function scrapeAshbyCompany(source) {
  try {
    const company = source.company;
    const board = source.board;

    console.log(`🟣 Ashby: ${company}`);

    const url = `https://jobs.ashbyhq.com/${board}`;

    const res = await fetchWithRetry(url);

    if (!res || !res.ok) {
      console.log(`❌ Failed: ${company}`);
      return;
    }

    const html = await res.text();

    const matches = [...html.matchAll(/href="([^"]+)"/g)];

    let count = 0;

    for (const m of matches) {
      const href = m[1];

      if (!href.includes("/job/")) continue;

      const applyLink = href.startsWith("http")
        ? href
        : `https://jobs.ashbyhq.com${href}`;

      const title =
        href.split("/").pop()?.replace(/-/g, " ") ||
        "Job Opening";

      await saveJob({
        title,
        company,
        location: "Global",
        work_mode: "Remote",
        job_type: detectJobType(title),
        company_description: getCompanyDescription(company),
        job_description: "",
        skills: null,
        apply_link: applyLink,
        source: "Ashby",
        company_logo: getCompanyLogo(source),
        salary: "Not disclosed",
        experience: detectExperience(title),
        education: "Not specified",
        department: "Not specified",
        posted_at: null
      });

      count++;
    }

    console.log(`✅ ${count} jobs from ${company}\n`);

  } catch (err) {
    console.log(`❌ Ashby error (${source.company}):`, err.message);
  }
}

// ======================
// WORKABLE SCRAPER
// ======================

async function scrapeWorkableCompany(source) {
  try {
    const company = source.company;
    const board = source.board;

    console.log(`🟡 Workable: ${company}`);

    const url =
      `https://apply.workable.com/api/v3/accounts/${board}/jobs`;

    const res = await fetchWithRetry(url);

    if (!res || !res.ok) {
      console.log(`❌ Failed: ${company}`);
      return;
    }

    const data = await res.json();

    const jobs = data.results || [];

    for (const job of jobs) {

      const title = job.title || "Untitled";

      const location =
        job.location?.location_str || "Remote";

      const applyLink =
        `https://apply.workable.com/${board}/j/${job.shortcode}`;

      await saveJob({
        title,
        company,
        location,
        work_mode: detectWorkMode(location),
        job_type: detectJobType(title),
        company_description: getCompanyDescription(company),
        job_description: "",
        skills: null,
        apply_link: applyLink,
        source: "Workable",
        company_logo: getCompanyLogo(source),
        salary: "Not disclosed",
        experience: detectExperience(title),
        education: "Not specified",
        department: "Not specified",
        posted_at: job.published || null
      });
    }

    console.log(`✅ ${jobs.length} jobs from ${company}\n`);

  } catch (err) {
    console.log(`❌ Workable error (${source.company}):`, err.message);
  }
}

// ======================
// ICIMS SCRAPER
// ======================

async function scrapeICIMSCompany(source) {
  try {
    const company = source.company;
    const board = source.board;

    console.log(`🔷 iCIMS: ${company}`);

    const url =
      source.url ||
      `https://${board}.icims.com/jobs/search?ss=1`;

    const res = await fetchWithRetry(url);

    if (!res || !res.ok) {
      console.log(`❌ Failed: ${company}`);
      return;
    }

    const html = await res.text();

    const matches = [
      ...html.matchAll(/href="([^"]*\/jobs\/[^"]+)"/g)
    ];

    let count = 0;

    for (const m of matches) {

      let applyLink = m[1];

      if (!applyLink.startsWith("http")) {
        applyLink = `https://${board}.icims.com${applyLink}`;
      }

      const title =
        applyLink.split("/").pop()?.replace(/-/g, " ") ||
        "Job Opening";

      await saveJob({
        title,
        company,
        location: "Global",
        work_mode: "Onsite",
        job_type: detectJobType(title),
        company_description: getCompanyDescription(company),
        job_description: "",
        skills: null,
        apply_link: applyLink,
        source: "iCIMS",
        company_logo: getCompanyLogo(source),
        salary: "Not disclosed",
        experience: detectExperience(title),
        education: "Not specified",
        department: "Not specified",
        posted_at: null
      });

      count++;
    }

    console.log(`✅ ${count} jobs from ${company}\n`);

  } catch (err) {
    console.log(`❌ iCIMS error (${source.company}):`, err.message);
  }
}

// ======================
// SUCCESSFACTORS SCRAPER
// ======================

async function scrapeSuccessFactorsCompany(source) {
  try {
    const company = source.company;
    const board = source.board;

    console.log(`🟢 SuccessFactors: ${company}`);

    const url =
      source.url ||
      `https://${board}.jobs2web.com/search/?q=&locationsearch=`;

    const res = await fetchWithRetry(url);

    if (!res || !res.ok) {
      console.log(`❌ Failed: ${company}`);
      return;
    }

    const html = await res.text();

    const matches = [
      ...html.matchAll(/href="([^"]*job\/[^"]+)"/g)
    ];

    let count = 0;

    for (const m of matches) {

      let applyLink = m[1];

      if (!applyLink.startsWith("http")) {
        applyLink = `https://${board}.jobs2web.com${applyLink}`;
      }

      const title =
        applyLink.split("/").pop()?.replace(/-/g, " ") ||
        "Job Opening";

      await saveJob({
        title,
        company,
        location: "Global",
        work_mode: "Onsite",
        job_type: detectJobType(title),
        company_description: getCompanyDescription(company),
        job_description: "",
        skills: null,
        apply_link: applyLink,
        source: "SuccessFactors",
        company_logo: getCompanyLogo(source),
        salary: "Not disclosed",
        experience: detectExperience(title),
        education: "Not specified",
        department: "Not specified",
        posted_at: null
      });

      count++;
    }

    console.log(`✅ ${count} jobs from ${company}\n`);

  } catch (err) {
    console.log(`❌ SuccessFactors error (${source.company}):`, err.message);
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
// MARK OLD JOBS INACTIVE
// ======================

async function markOldJobsInactive() {
  try {

    await pool.query(`
      UPDATE jobs
      SET is_active = false
      WHERE source IN
      (
        'Lever',
        'Greenhouse',
        'SmartRecruiters',
        'Workday',
        'Ashby',
        'Workable',
        'iCIMS',
        'SuccessFactors'
      )
    `);

    console.log("♻️ Old ATS jobs marked inactive\n");

  } catch (err) {
    console.log("Inactive update error:", err.message);
  }
}

// ======================
// HELPERS
// ======================

async function fetchWithRetry(url, options = {}, retries = 3) {

  for (let attempt = 1; attempt <= retries; attempt++) {

    try {

      const controller = new AbortController();

      const timeout = setTimeout(
        () => controller.abort(),
        30000
      );

      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });

      clearTimeout(timeout);

      return response;

    } catch (err) {

      console.log(
        `Fetch attempt ${attempt} failed:`,
        err.message
      );

      if (attempt === retries) {
        return null;
      }

      await sleep(1000 * attempt);
    }
  }

  return null;
}

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
    "Node.js",
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "SQL",
    "PostgreSQL",
    "MongoDB",
    "Android",
    "Kotlin",
    "Swift",
    "C++",
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
    "Linux"
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

  if (
    text.includes("part time") ||
    text.includes("part-time")
  ) {
    return "Part Time";
  }

  return "Full Time";
}

function detectExperience(text) {

  if (!text) return "Not specified";

  text = String(text).toLowerCase();

  if (text.includes("intern")) return "Internship";

  if (
    text.includes("fresher") ||
    text.includes("entry level") ||
    text.includes("graduate")
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
    text.includes("lead")
  ) {
    return "3+ yrs";
  }

  return "Not specified";
}

function detectEducation(text) {

  if (!text) return "Not specified";

  text = String(text).toLowerCase();

  if (text.includes("b.tech")) return "B.Tech";
  if (text.includes("bachelor")) return "Bachelor's Degree";
  if (text.includes("master")) return "Master's Degree";
  if (text.includes("mba")) return "MBA";

  return "Not specified";
}

function extractSalary(text) {

  if (!text) return "Not disclosed";

  const regex =
    /(?:₹|INR|\$|USD)\s?[\d,]+(?:\s?-\s?(?:₹|INR|\$|USD)?\s?[\d,]+)?/i;

  const match = String(text).match(regex);

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

function getCompanyLogo(source) {

  const domain =
    source.domain ||
    `${String(source.company)
      .replace(/\s+/g, "")
      .toLowerCase()}.com`;

  if (!LOGO_DEV_TOKEN) {
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=128`;
  }

  return `https://img.logo.dev/${domain}?token=${LOGO_DEV_TOKEN}`;
}

function getCompanyDescription(company) {
  return `${company} is a leading company offering technology, engineering, product, analytics, operations, support, and business career opportunities.`;
}

function cleanText(value) {

  if (value === undefined || value === null) {
    return null;
  }

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

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ======================
// START
// ======================

runScraper();