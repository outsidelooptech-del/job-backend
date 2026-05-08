const fetch = require("node-fetch");
const { Pool } = require("pg");

const pool = new Pool({
  connectionString: "postgresql://neondb_owner:npg_GdSTEZXgkL27@ep-green-shadow-an0gznda-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
  ssl: { rejectUnauthorized: false }
});

// 🔥 COMPANY LIST (tested mix)
const leverCompanies = [
  "spotify",
  "netflix",
  "figma",
  "coinbase",
  "rippling"
];

const greenhouseCompanies = [
  "airbnb",
  "stripe",
  "shopify",
  "robinhood",
  "notion"
];

// 🚀 MAIN SCRAPER
async function runScraper() {
  try {
    console.log("🧹 Clearing old jobs...");

    // ======================
    // 🔵 LEVER
    // ======================
    for (let company of leverCompanies) {
      console.log("\nFetching Lever:", company);

      try {
        const res = await fetch(`https://api.lever.co/v0/postings/${company}`);

        if (!res.ok) {
          console.log("❌ Failed:", company);
          continue;
        }

        const jobs = await res.json();

        for (let job of jobs) {
        await insertJob({
  title: job.text,
  company: company,
  location: job.categories?.location || "Remote",
  work_mode: job.categories?.workplaceType || null,
  job_type: job.categories?.commitment || "Full Time",
  description: job.descriptionPlain || "",
  skills: extractSkills(job.descriptionPlain),
  apply_link: job.hostedUrl,
  source: "Lever"
});
        }

        console.log(`✅ ${jobs.length} jobs from ${company}`);

      } catch (err) {
        console.log("❌ Lever error:", company);
      }
    }

    // ======================
    // 🟢 GREENHOUSE
    // ======================
    for (let company of greenhouseCompanies) {
      console.log("\nFetching Greenhouse:", company);

      try {
        const res = await fetch(`https://boards-api.greenhouse.io/v1/boards/${company}/jobs`);

        if (!res.ok) {
          console.log("❌ Failed:", company);
          continue;
        }

        const data = await res.json();
        const jobs = data.jobs || [];

        for (let job of jobs) {
          let workMode = null;

          if (job.metadata) {
            const wm = job.metadata.find(m => m.name === "Workplace Type");
            if (wm) workMode = wm.value;
          }

     await insertJob({
  title: job.title,
  company: company,
  location: job.location?.name || "Remote",
  work_mode: workMode,
  job_type: "Full Time",
  description: "",
  skills: null,
  apply_link: job.absolute_url,
  source: "Greenhouse"
});
        }

        console.log(`✅ ${jobs.length} jobs from ${company}`);

      } catch (err) {
        console.log("❌ Greenhouse error:", company);
      }
    }

    console.log("\n🚀 ALL DONE");

  } catch (err) {
    console.error("❌ Fatal error:", err);
  }
}

// ======================
// 📥 INSERT FUNCTION
// ======================
async function insertJob(job) {
  try {
    await pool.query(
      `INSERT INTO jobs 
      (title, company, location, work_mode, job_type, job_description, skills, apply_link, source, is_active)
      VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,true)
      ON CONFLICT (apply_link)
      DO UPDATE SET
        title = EXCLUDED.title,
        company = EXCLUDED.company,
        location = EXCLUDED.location,
        work_mode = EXCLUDED.work_mode,
        job_type = EXCLUDED.job_type,
        job_description = EXCLUDED.job_description,
        skills = EXCLUDED.skills,
        source = EXCLUDED.source,
        is_active = true`,
      [
        job.title,
        job.company,
        job.location,
        job.work_mode,
        job.job_type,
        job.description,
        job.skills,
        job.apply_link,
        job.source
      ]
    );

    console.log("✔", job.title);

  } catch (err) {
    console.log("Insert error:", err.message);
  }
}

// ======================
// 🧠 BASIC SKILL EXTRACTOR
// ======================
function extractSkills(text) {
  if (!text) return null;

  const skills = [
    "Python",
    "Java",
    "JavaScript",
    "SQL",
    "React",
    "Node",
    "AWS",
    "Docker",
    "Kubernetes",
    "C++"
  ];

  return skills
    .filter(skill => text.toLowerCase().includes(skill.toLowerCase()))
    .join(", ");
}

// 🚀 RUN
runScraper();
