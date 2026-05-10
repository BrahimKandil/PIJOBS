import numpy as np
import pandas as pd
import re
from sklearn.preprocessing import MultiLabelBinarizer


def clean_and_parse_skills(x):
    if pd.isna(x):
        return []
    x = str(x).lower().replace("[", "").replace("]", "").replace("'", "")
    return [s.strip() for s in x.split(",") if len(s.strip()) > 2]


def normalize(skill):
    if "python" in skill: return "python"
    if "sql" in skill: return "sql"
    if "power" in skill: return "powerbi"
    if "aws" in skill: return "aws"
    if "azure" in skill: return "azure"
    if "gcp" in skill: return "gcp"
    if "docker" in skill: return "docker"
    if "kubernetes" in skill: return "kubernetes"
    return skill


def normalize_list(skills):
    return list(set([normalize(s) for s in skills if s]))


def build_features(df):

    df = df.copy()

    # -------------------------
    # CLEAN TARGET FIRST
    # -------------------------
    df = df.dropna(subset=["salary_year_avg"])

    y = np.log1p(df["salary_year_avg"])

    # -------------------------
    # DATE FEATURES
    # -------------------------
    df["job_posted_date"] = pd.to_datetime(df["job_posted_date"], errors="coerce")

    df["year"] = df["job_posted_date"].dt.year
    df["month"] = df["job_posted_date"].dt.month
    df["dayofweek"] = df["job_posted_date"].dt.dayofweek

    # -------------------------
    # SKILLS
    # -------------------------
    df["job_skills"] = df["job_skills"].fillna("[]")

    df["job_skills"] = df["job_skills"].apply(clean_and_parse_skills)
    df["job_skills"] = df["job_skills"].apply(normalize_list)

    # remove empty rows
    mask = df["job_skills"].map(len) > 0
    df = df[mask].reset_index(drop=True)
    y = y[mask].reset_index(drop=True)

    # -------------------------
    # BASE FEATURES
    # -------------------------
    X = df[
        [
            "job_title_short",
            "job_country",
            "job_work_from_home",
            "job_no_degree_mention",
            "job_schedule_type",
            "year",
            "month",
            "dayofweek",
            "company_name"
        ]
    ].fillna("unknown")

    for c in ["job_work_from_home", "job_no_degree_mention"]:
        X[c] = X[c].astype(int)

    # -------------------------
    # SKILL ENCODING
    # -------------------------
    mlb = MultiLabelBinarizer()

    skills = pd.DataFrame(
        mlb.fit_transform(df["job_skills"]),
        columns=mlb.classes_,
        index=df.index
    )

    top = skills.sum().sort_values(ascending=False).head(50).index
    skills = skills[top].reset_index(drop=True)

    X = X.reset_index(drop=True)

    return pd.concat([X, skills], axis=1), y, mlb