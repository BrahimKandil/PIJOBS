import pandas as pd
from collections import Counter


# =========================================
# DATASET PATH
# =========================================
fileName = "data/full_jobs_dataset.csv"


# =========================================
# CLEAN SKILLS
# =========================================
def clean_and_parse_skills(x):

    # null protection
    if pd.isna(x):
        return []

    # convert to lowercase string
    x = str(x).lower()

    # remove brackets and quotes
    x = x.replace("[", "")
    x = x.replace("]", "")
    x = x.replace("'", "")

    # split by comma
    skills = x.split(",")

    # clean spaces
    skills = [
        s.strip()
        for s in skills
        if len(s.strip()) > 2
    ]

    return skills


# =========================================
# NORMALIZE SKILL NAMES
# =========================================
def normalize(skill):

    if "python" in skill:
        return "python"

    if "sql" in skill:
        return "sql"

    if "power" in skill:
        return "powerbi"

    if "aws" in skill:
        return "aws"

    if "azure" in skill:
        return "azure"

    if "gcp" in skill:
        return "gcp"

    if "docker" in skill:
        return "docker"

    if "kubernetes" in skill:
        return "kubernetes"

    return skill


# =========================================
# NORMALIZE FULL LIST
# =========================================
def normalize_list(skills):

    normalized = []

    for s in skills:

        s = normalize(s)

        if s:
            normalized.append(s)

    # remove duplicates
    return list(set(normalized))


# =========================================
# MAIN FUNCTION
# =========================================
def get_common_skills(top_n=50):

    # -------------------------
    # LOAD CSV
    # -------------------------
    df = pd.read_csv(fileName)

    # -------------------------
    # CLEAN COLUMN
    # -------------------------
    df["job_skills"] = df["job_skills"].fillna("[]")

    # -------------------------
    # PARSE SKILLS
    # -------------------------
    df["job_skills"] = df["job_skills"].apply(
        clean_and_parse_skills
    )

    # -------------------------
    # NORMALIZE
    # -------------------------
    df["job_skills"] = df["job_skills"].apply(
        normalize_list
    )

    # -------------------------
    # COLLECT ALL SKILLS
    # -------------------------
    all_skills = []

    for skills in df["job_skills"]:

        all_skills.extend(skills)

    # -------------------------
    # COUNT FREQUENCY
    # -------------------------
    counter = Counter(all_skills)

    # -------------------------
    # TAKE TOP N
    # -------------------------
    common_skills = [
        skill
        for skill, count in counter.most_common(top_n)
    ]

    return common_skills


# =========================================
# TEST
# =========================================
COMMON_SKILLS = get_common_skills()

print(COMMON_SKILLS)