const express = require("express");
const cors = require("cors");
const { Pool } = require("pg");

const app = express();
app.use(cors());
app.use(express.json());

// Neon DB connection
const pool = new Pool({
  connectionString: "postgresql://neondb_owner:npg_GdSTEZXgkL27@ep-green-shadow-an0gznda.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require",
  ssl: { rejectUnauthorized: false }
});

// GET all jobs
app.get("/jobs", async (req, res) => {
  try {
    const result = await pool.query(
      "SELECT * FROM jobs ORDER BY created_at DESC"
    );
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// test route
app.get("/", (req, res) => {
  res.send("Job API is running 🚀");
});

app.listen(3000, () => {
  console.log("Server running on port 3000");
});