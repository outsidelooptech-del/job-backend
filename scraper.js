import fetch from "node-fetch";
import pkg from "pg";
const { Pool } = pkg;

// 🔴 PUT YOUR NEON DB URL HERE
const pool = new Pool({
  connectionString: "YOUR_NEON_DB_URL",
  ssl: { rejectUnauthorized: false }
});

// ✅ LIST OF COMPANIES (start small)
const companies = ["spotify", "airbnb", "stripe"];

async function fetchAndInsert() {
  for (let company of companies) {

    console.log("Fetching:", company);

    try {
      const res = await fetch(`https://api.lever.co/v0/postings/${company}`);
      const jobs = await res.json();

      console.log(`Found ${jobs.length} jobs`);

      for (let job of jobs) {

        try {
          await pool.query(
            `INSERT INTO jobs 
            (title, company, location, job_description, apply_link)
            VALUES ($1,$2,$3,$4,$5)
            ON CONFLICT (apply_link) DO NOTHING`,
            [
              job.text,
              company,
              job.categories.location || "Remote",
              job.descriptionPlain || "",
              job.hostedUrl
            ]
          );

          console.log("Inserted:", job.text);

        } catch (err) {
          console.log("Insert error:", err.message);
        }
      }

    } catch (err) {
      console.log("Fetch error:", company);
    }
  }

  console.log("✅ DONE");
}

fetchAndInsert();