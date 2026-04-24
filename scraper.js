const fetch = require("node-fetch");
const { Pool } = require("pg");

const pool = new Pool({
  connectionString: "postgresql://neondb_owner:npg_GdSTEZXgkL27@ep-green-shadow-an0gznda-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require",
  ssl: { rejectUnauthorized: false }
});

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
      console.log("Fetch error:", company, err.message);
    }
  }

  console.log("✅ DONE");
}

fetchAndInsert();
