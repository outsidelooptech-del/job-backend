from fastapi import FastAPI
from database import get_connection
from psycopg2.extras import RealDictCursor

app = FastAPI()


# ----------------------------
# ROOT
# ----------------------------

@app.get("/")
def home():
    return {"message": "Job API is running 🚀"}


# ----------------------------
# GET ALL JOBS
# ----------------------------

@app.get("/jobs")
def get_jobs(limit: int = 50):

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT * FROM jobs
        ORDER BY id DESC
        LIMIT %s
    """, (limit,))

    jobs = cursor.fetchall()

    cursor.close()
    conn.close()

    return jobs


# ----------------------------
# FILTER BY COMPANY
# ----------------------------

@app.get("/jobs/company/{company_name}")
def get_jobs_by_company(company_name: str):

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT * FROM jobs
        WHERE company ILIKE %s
        ORDER BY id DESC
    """, (f"%{company_name}%",))

    jobs = cursor.fetchall()

    cursor.close()
    conn.close()

    return jobs


# ----------------------------
# SEARCH BY KEYWORD
# ----------------------------

@app.get("/jobs/search")
def search_jobs(keyword: str):

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute("""
        SELECT * FROM jobs
        WHERE title ILIKE %s
        OR location ILIKE %s
        OR keywords::text ILIKE %s
        ORDER BY id DESC
    """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"))

    jobs = cursor.fetchall()

    cursor.close()
    conn.close()

    return jobs