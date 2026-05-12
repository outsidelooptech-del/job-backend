const express = require("express");
const cors = require("cors");
const { Pool } = require("pg");
require("dotenv").config();

const app = express();

app.use(cors());
app.use(express.json());

// ======================================
// DB CONNECTION
// ======================================

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: false
  }
});

// ======================================
// SAFE JOB FIELDS
// ======================================

const JOB_FIELDS = `
  id,
  title,
  company,
  location,
  work_mode,
  job_type,
  company_description,
  job_description,
  skills,
  apply_link,
  views,
  created_at,
  company_logo,
  salary,
  experience,
  education,
  department,
  source,
  posted_at,
  is_active,
  updated_at,
  company_slug,
  job_slug,
  category,
  source_priority
`;

// ======================================
// HELPERS
// ======================================

function buildFilters(req) {
  let query = `
    FROM jobs
    WHERE is_active = true
  `;

  const values = [];
  let index = 1;

  if (req.query.keyword) {
    query += `
      AND (
        LOWER(title) LIKE LOWER($${index})
        OR LOWER(company) LIKE LOWER($${index})
        OR LOWER(COALESCE(skills, '')) LIKE LOWER($${index})
        OR LOWER(location) LIKE LOWER($${index})
        OR LOWER(COALESCE(category, '')) LIKE LOWER($${index})
      )
    `;

    values.push(`%${req.query.keyword}%`);
    index++;
  }

  if (req.query.company) {
    query += ` AND LOWER(company_slug) = LOWER($${index}) `;
    values.push(req.query.company);
    index++;
  }

  if (req.query.category) {
    query += ` AND LOWER(category) = LOWER($${index}) `;
    values.push(req.query.category.toLowerCase());
    index++;
  }

  if (req.query.location) {
    query += ` AND LOWER(location) LIKE LOWER($${index}) `;
    values.push(`%${req.query.location}%`);
    index++;
  }

  if (req.query.work_mode) {
    query += ` AND LOWER(work_mode) = LOWER($${index}) `;
    values.push(req.query.work_mode.toLowerCase());
    index++;
  }

  if (req.query.job_type) {
    query += ` AND LOWER(job_type) = LOWER($${index}) `;
    values.push(req.query.job_type.toLowerCase());
    index++;
  }

  if (req.query.experience) {
    query += ` AND LOWER(experience) LIKE LOWER($${index}) `;
    values.push(`%${req.query.experience}%`);
    index++;
  }

  return {
    query,
    values,
    index
  };
}

// ======================================
// GET JOBS
// ======================================

app.get("/api/jobs", async (req, res) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 20;
    const offset = (page - 1) * limit;

    const built = buildFilters(req);

    const countQuery = `
      SELECT COUNT(*) as total
      ${built.query}
    `;

    const countResult = await pool.query(countQuery, built.values);
    const total = parseInt(countResult.rows[0].total);

    let orderBy = `
      ORDER BY source_priority DESC, created_at DESC
    `;

    if (req.query.sort === "latest") {
      orderBy = ` ORDER BY created_at DESC `;
    }

    if (req.query.sort === "views") {
      orderBy = ` ORDER BY views DESC `;
    }

    const jobsQuery = `
      SELECT ${JOB_FIELDS}
      ${built.query}
      ${orderBy}
      LIMIT $${built.index}
      OFFSET $${built.index + 1}
    `;

    const result = await pool.query(jobsQuery, [
      ...built.values,
      limit,
      offset
    ]);

    res.json({
      success: true,
      jobs: result.rows,
      pagination: {
        page,
        limit,
        total,
        total_pages: Math.ceil(total / limit),
        has_next: page * limit < total
      }
    });
  } catch (err) {
    console.log(err);

    res.status(500).json({
      success: false,
      error: err.message
    });
  }
});

// ======================================
// GET LATEST JOBS
// ======================================

app.get("/api/jobs/latest", async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT ${JOB_FIELDS}
      FROM jobs
      WHERE is_active = true
      ORDER BY created_at DESC
      LIMIT 20
    `);

    res.json({
      success: true,
      jobs: result.rows
    });
  } catch (err) {
    res.status(500).json({
      success: false,
      error: err.message
    });
  }
});

// ======================================
// GET SINGLE JOB
// ======================================

app.get("/api/jobs/id/:id", async (req, res) => {
  try {
    const result = await pool.query(
      `
      SELECT ${JOB_FIELDS}
      FROM jobs
      WHERE id = $1
      `,
      [req.params.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        success: false,
        error: "Job not found"
      });
    }

    res.json({
      success: true,
      job: result.rows[0]
    });
  } catch (err) {
    res.status(500).json({
      success: false,
      error: err.message
    });
  }
});

// ======================================
// GET COMPANY JOBS
// ======================================

app.get("/api/company/:slug", async (req, res) => {
  try {
    const result = await pool.query(
      `
      SELECT ${JOB_FIELDS}
      FROM jobs
      WHERE company_slug = $1
      AND is_active = true
      ORDER BY created_at DESC
      `,
      [req.params.slug]
    );

    res.json({
      success: true,
      jobs: result.rows
    });
  } catch (err) {
    res.status(500).json({
      success: false,
      error: err.message
    });
  }
});

// ======================================
// GET CATEGORY JOBS
// ======================================

app.get("/api/category/:category", async (req, res) => {
  try {
    const result = await pool.query(
      `
      SELECT ${JOB_FIELDS}
      FROM jobs
      WHERE LOWER(category) = LOWER($1)
      AND is_active = true
      ORDER BY created_at DESC
      `,
      [req.params.category]
    );

    res.json({
      success: true,
      jobs: result.rows
    });
  } catch (err) {
    res.status(500).json({
      success: false,
      error: err.message
    });
  }
});

// ======================================
// AI JOB MATCH API
// ======================================

app.post("/api/jobs/match", async (req, res) => {
  try {
    const {
      qualification,
      batch,
      role,
      skills,
      location
    } = req.body;

    const skillText = Array.isArray(skills)
      ? skills.join(" ")
      : (skills || "");

    const searchText = `${role || ""} ${skillText || ""}`.trim();

    const locationFilter =
      location && location !== "Any Location"
        ? `%${location}%`
        : "";

    const result = await pool.query(
      `
      SELECT
        ${JOB_FIELDS},
        (
          CASE
            WHEN LOWER(title) LIKE LOWER($1) THEN 35
            WHEN LOWER(COALESCE(category, '')) LIKE LOWER($1) THEN 25
            ELSE 0
          END
          +
          CASE
            WHEN LOWER(COALESCE(skills, '')) LIKE LOWER($2) THEN 30
            WHEN LOWER(COALESCE(job_description, '')) LIKE LOWER($2) THEN 20
            ELSE 0
          END
          +
          CASE
            WHEN $3 = '' THEN 0
            WHEN LOWER(location) LIKE LOWER($3) THEN 15
            WHEN LOWER(work_mode) = 'remote'
              AND LOWER($3) LIKE '%remote%' THEN 15
            ELSE 0
          END
          +
          CASE
            WHEN $4 = '' THEN 0
            WHEN LOWER(COALESCE(education, '')) LIKE LOWER($4) THEN 10
            WHEN LOWER(COALESCE(education, '')) = 'not specified' THEN 5
            ELSE 0
          END
          +
          CASE
            WHEN $5 = '' THEN 0
            WHEN LOWER(COALESCE(experience, '')) LIKE LOWER($5) THEN 10
            WHEN LOWER(COALESCE(experience, '')) = 'not specified' THEN 4
            ELSE 0
          END
        ) AS match_score
      FROM jobs
      WHERE is_active = true
      AND (
        LOWER(title) LIKE LOWER($1)
        OR LOWER(COALESCE(category, '')) LIKE LOWER($1)
        OR LOWER(COALESCE(skills, '')) LIKE LOWER($2)
        OR LOWER(COALESCE(job_description, '')) LIKE LOWER($2)
        OR ($3 <> '' AND LOWER(location) LIKE LOWER($3))
      )
      ORDER BY
        match_score DESC,
        source_priority DESC,
        created_at DESC
      LIMIT 50
      `,
      [
        `%${role || ""}%`,
        `%${skillText || searchText}%`,
        locationFilter,
        qualification ? `%${qualification}%` : "",
        batch ? `%${batch}%` : ""
      ]
    );

    res.json({
      success: true,
      profile: {
        qualification,
        batch,
        role,
        skills,
        location
      },
      jobs: result.rows
    });
  } catch (err) {
    console.log("Match API error:", err);

    res.status(500).json({
      success: false,
      error: err.message
    });
  }
});

// ======================================
// INCREMENT VIEWS
// ======================================

app.post("/api/jobs/:id/view", async (req, res) => {
  try {
    await pool.query(
      `
      UPDATE jobs
      SET views = views + 1
      WHERE id = $1
      `,
      [req.params.id]
    );

    res.json({
      success: true
    });
  } catch (err) {
    res.status(500).json({
      success: false,
      error: err.message
    });
  }
});

// ======================================
// TEST ROUTE
// ======================================

app.get("/", (req, res) => {
  res.send("🚀 Off Camp Job API Running");
});

// ======================================
// START SERVER
// ======================================

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});