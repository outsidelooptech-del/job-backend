const express = require("express");
const cors = require("cors");
const { Pool } = require("pg");

const app = express();

app.use(cors());
app.use(express.json());

// ======================
// DB CONNECTION
// ======================
const pool = new Pool({
  connectionString:
    "postgresql://neondb_owner:npg_GdSTEZXgkL27@ep-green-shadow-an0gznda.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require",
  ssl: { rejectUnauthorized: false }
});

// ======================
// GET JOBS API
// ======================
app.get("/jobs", async (req, res) => {
  try {

    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;

    const offset = (page - 1) * limit;

    const company = req.query.company || "";
    const location = req.query.location || "";
    const type = req.query.type || "";
    const experience = req.query.experience || "";
    const keyword = req.query.keyword || "";

    let query = `
      SELECT *
      FROM jobs
      WHERE is_active = true
    `;

    const values = [];
    let index = 1;

    // ======================
    // SEARCH KEYWORD
    // ======================
    if (keyword) {
      query += `
        AND (
          LOWER(title) LIKE LOWER($${index})
          OR LOWER(company) LIKE LOWER($${index})
          OR LOWER(skills) LIKE LOWER($${index})
          OR LOWER(location) LIKE LOWER($${index})
        )
      `;
      values.push(`%${keyword}%`);
      index++;
    }

    // ======================
    // COMPANY FILTER
    // ======================
    if (company) {
      query += ` AND LOWER(company) LIKE LOWER($${index}) `;
      values.push(`%${company}%`);
      index++;
    }

    // ======================
    // LOCATION FILTER
    // ======================
    if (location) {
      query += ` AND LOWER(location) LIKE LOWER($${index}) `;
      values.push(`%${location}%`);
      index++;
    }

    // ======================
    // TYPE FILTER
    // ======================
    if (type) {
      query += ` AND LOWER(job_type) LIKE LOWER($${index}) `;
      values.push(`%${type}%`);
      index++;
    }

    // ======================
    // EXPERIENCE FILTER
    // ======================
    if (experience) {
      query += ` AND LOWER(experience) LIKE LOWER($${index}) `;
      values.push(`%${experience}%`);
      index++;
    }

    // ======================
    // ORDER + PAGINATION
    // ======================
    query += `
      ORDER BY created_at DESC
      LIMIT $${index}
      OFFSET $${index + 1}
    `;

    values.push(limit);
    values.push(offset);

    const result = await pool.query(query, values);

    res.json({
      jobs: result.rows,
      page,
      limit,
      count: result.rows.length
    });

  } catch (err) {
    console.log(err);

    res.status(500).json({
      error: err.message
    });
  }
});

// ======================
// TEST ROUTE
// ======================
app.get("/", (req, res) => {
  res.send("Job API is running 🚀");
});

// ======================
// START SERVER
// ======================
app.listen(3000, () => {
  console.log("Server running on port 3000");
});