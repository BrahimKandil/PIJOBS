import os
import pyodbc
import pandas as pd

from django.db.models import Max

from accounts.models import  Candidature,RecruiterProfile
def get_or_create(cursor, table, key_col, key_val, insert_sql, params):
    """
    Helper: returns ID from dimension (or inserts if missing)
    """
    cursor.execute(f"SELECT {key_col} FROM {table} WHERE {key_col} = ?", key_val)
    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute(insert_sql, params)
    return key_val
import pyodbc


def get_or_create(cursor, table, field, value, insert_query, insert_values):
    """
    Generic helper for dimension tables
    """

    cursor.execute(
        f"SELECT {table.split('_')[1].lower()}_id FROM {table} WHERE {field} = ?",
        value
    )

    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute(insert_query, insert_values)

    cursor.execute(
        f"SELECT {table.split('_')[1].lower()}_id FROM {table} WHERE {field} = ?",
        value
    )

    row = cursor.fetchone()

    return row[0] if row else None


def run_daily_etl():

    conn = None

    try:
        print("Starting Daily ETL...")

        candidatures = Candidature.objects.filter(
            situation="accepted",
            imported=False
        ).select_related(
            "candidate",
            "candidate__user",
            "post",
            "post__recruiter"
        )

        # ----------------------------
        # SQL SERVER CONNECTION
        # ----------------------------
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

        cursor = conn.cursor()

        # ----------------------------
        # LAST FACT ID
        # ----------------------------
        cursor.execute("SELECT ISNULL(MAX(job_id), 0) FROM Fact_Job")
        last_job_id = cursor.fetchone()[0]

        # ============================
        # LOOP THROUGH CANDIDATURES
        # ============================
        for cand in candidatures:

            # recruiter is already RecruiterProfile
            recruiter_profile = cand.post.recruiter

            # ============================
            # DIM JOB TITLE
            # ============================
            job_title = cand.post.title

            cursor.execute("""
                SELECT job_title_id
                FROM Dim_JobTitle
                WHERE job_title_short = ?
            """, (job_title,))

            row = cursor.fetchone()

            if row:
                job_title_id = row[0]
            else:
                cursor.execute("""
                    INSERT INTO Dim_JobTitle (
                        job_title_short,
                        job_title
                    )
                    VALUES (?, ?)
                """, (
                    job_title,
                    job_title
                ))

                cursor.execute("""
                    SELECT job_title_id
                    FROM Dim_JobTitle
                    WHERE job_title_short = ?
                """, (job_title,))

                job_title_id = cursor.fetchone()[0]

            # ============================
            # DIM LOCATION
            # ============================
            location = getattr(recruiter_profile, "location", None)

            cursor.execute("""
                SELECT location_id
                FROM Dim_Location
                WHERE job_location = ?
            """, (location,))

            row = cursor.fetchone()

            if row:
                location_id = row[0]
            else:
                cursor.execute("""
                    INSERT INTO Dim_Location (
                        job_location,
                        search_location,
                        job_country
                    )
                    VALUES (?, ?, ?)
                """, (
                    location,
                    location,
                    getattr(recruiter_profile, "address", None)
                ))

                cursor.execute("""
                    SELECT location_id
                    FROM Dim_Location
                    WHERE job_location = ?
                """, (location,))

                location_id = cursor.fetchone()[0]

            # ============================
            # DIM COMPANY
            # ============================
            company = getattr(recruiter_profile, "company_name", None)

            cursor.execute("""
                SELECT company_id
                FROM Dim_Company
                WHERE company_name = ?
            """, (company,))

            row = cursor.fetchone()

            if row:
                company_id = row[0]
            else:
                cursor.execute("""
                    INSERT INTO Dim_Company (
                        company_name,
                        job_health_insurance
                    )
                    VALUES (?, ?)
                """, (
                    company,
                    False
                ))

                cursor.execute("""
                    SELECT company_id
                    FROM Dim_Company
                    WHERE company_name = ?
                """, (company,))

                company_id = cursor.fetchone()[0]

            # ============================
            # DIM JOB TYPE
            # ============================
            job_type = cand.post.domain

            cursor.execute("""
                SELECT job_type_id
                FROM Dim_JobType
                WHERE job_schedule_type = ?
            """, (job_type,))

            row = cursor.fetchone()

            if row:
                job_type_id = row[0]
            else:
                cursor.execute("""
                    INSERT INTO Dim_JobType (
                        job_schedule_type,
                        job_work_from_home,
                        job_type_skills
                    )
                    VALUES (?, ?, ?)
                """, (
                    job_type,
                    False,
                    cand.post.required_skills
                ))

                cursor.execute("""
                    SELECT job_type_id
                    FROM Dim_JobType
                    WHERE job_schedule_type = ?
                """, (job_type,))

                job_type_id = cursor.fetchone()[0]

            # ============================
            # DIM SKILLS
            # ============================
            skills = cand.candidate.skills

            cursor.execute("""
                SELECT skill_id
                FROM Dim_Skills
                WHERE job_skills = ?
            """, (skills,))

            row = cursor.fetchone()

            if row:
                skills_id = row[0]
            else:
                cursor.execute("""
                    INSERT INTO Dim_Skills (
                        job_skills
                    )
                    VALUES (?)
                """, (skills,))

                cursor.execute("""
                    SELECT skill_id
                    FROM Dim_Skills
                    WHERE job_skills = ?
                """, (skills,))

                skills_id = cursor.fetchone()[0]

            # ============================
            # FACT TABLE INSERT
            # ============================
            last_job_id += 1

            cursor.execute("""
                INSERT INTO Fact_Job (
                    job_id,
                    job_title_id,
                    location_id,
                    company_id,
                    job_type_id,
                    skills_id,
                    job_via,
                    job_posted_date,
                    job_no_degree_mention,
                    salary_rate,
                    salary_year_avg,
                    salary_hour_avg
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                last_job_id,
                job_title_id,
                location_id,
                company_id,
                job_type_id,
                skills_id,
                None,
                cand.date_of_post,
                False,
                None,
                None,
                None
            ))

            print(f"Imported candidature ID: {cand.id}")

        # ============================
        # COMMIT
        # ============================
        conn.commit()

        # ============================
        # UPDATE IMPORT FLAG
        # ============================
        candidatures.update(imported=True)

        print("ETL completed successfully.")

    except Exception as e:

        if conn:
            conn.rollback()

        print("ETL ERROR:", str(e))

    finally:

        if conn:
            conn.close()

        print("SQL connection closed.")

from apscheduler.schedulers.background import BackgroundScheduler

def start_scheduler():
    scheduler = BackgroundScheduler()

    # Run every day at 02:00
    # scheduler.add_job(
    #     run_daily_etl,
    #     'cron',
    #     hour=2,
    #     minute=0
    # )
    scheduler.add_job(
        run_daily_etl,
        'interval',
        minutes=5
    )

    scheduler.start()