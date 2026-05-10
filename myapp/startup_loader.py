import pandas as pd
import pyodbc
import os

def export_datawarehouse_to_csv():
    try:
        # conn = pyodbc.connect(
        #     "DRIVER={ODBC Driver 17 for SQL Server};"
        #     "SERVER=localhost\SQLEXPRESS;"
        #     "DATABASE=PI_JoBs;"
        #     "Trusted_Connection=yes;"
        # )
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=3alinfo-equipepicosoft.database.windows.net;"
            "DATABASE=PI_JoBs;"
            "UID=brahim;"
            "PWD=PicoSoft123;"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )

        query = """
        SELECT 
            f.job_id,

            jt.job_title_short,
            jt.job_title,

            l.job_location,
            l.search_location,
            l.job_country,

            c.company_name,
            c.job_health_insurance,

            t.job_schedule_type,
            t.job_work_from_home,
            t.job_type_skills,

            s.job_skills,

            f.job_via,
            f.job_posted_date,
            f.job_no_degree_mention,
            f.salary_rate,
            f.salary_year_avg,
            f.salary_hour_avg

        FROM Fact_Job f
        JOIN Dim_JobTitle jt ON f.job_title_short = jt.job_title_short
        JOIN Dim_Location l ON f.job_location = l.job_location
        JOIN Dim_Company c ON f.company_name = c.company_name
        JOIN Dim_JobType t ON f.job_schedule_type = t.job_schedule_type
        JOIN Dim_Skills s ON f.job_skills = s.job_skills
        """

        df = pd.read_sql(query, conn)

        os.makedirs("data", exist_ok=True)

        df.to_csv("data/full_jobs_dataset.csv", index=False, encoding="utf-8-sig")

        print("CSV generated successfully.")
        return True

    except Exception as e:
        print("Export error:", e)