import os
import json
import pickle
import pandas as pd

from accounts.ai_engine.cv_extractor import extract_cv_text

CLUSTER_PATH = "ml_models/clusters.txt"


# ==================================================
# SAVE CLUSTERS
# ==================================================
def save_clusters(post_id, clusters_dict):

    os.makedirs("ml_models", exist_ok=True)

    all_data = {}

    if os.path.exists(CLUSTER_PATH):

        with open(CLUSTER_PATH, "r") as f:

            try:
                all_data = json.load(f)
            except:
                all_data = {}

    all_data[str(post_id)] = clusters_dict

    with open(CLUSTER_PATH, "w") as f:
        json.dump(all_data, f, indent=4)


# ==================================================
# LOAD CLUSTERS
# ==================================================
def load_clusters(post_id):

    if not os.path.exists(CLUSTER_PATH):

        return {
            "senior": [],
            "intermediate": [],
            "junior": []
        }

    with open(CLUSTER_PATH, "r") as f:

        try:
            data = json.load(f)
        except:
            data = {}

    return data.get(
        str(post_id),
        {
            "senior": [],
            "intermediate": [],
            "junior": []
        }
    )


# ==================================================
# LOAD MODEL
# ==================================================
def load_clustering_model():

    bundle = pickle.load(
        open("ml_models/clustering.pkl", "rb")
    )

    return (
        bundle["model"],
        bundle["preprocessor"]
    )


# ==================================================
# MAIN CLUSTERING
# ==================================================
def cluster_candidates(candidatures, post_id):

    model, preprocessor = load_clustering_model()

    rows = []
    ids = []

    for c in candidatures:

        profile = c.candidate

        cv_text = ""

        try:

            if hasattr(profile, "cv") and profile.cv:
                cv_text = extract_cv_text(
                    profile.cv.path
                )

        except:
            cv_text = ""

        rows.append({

            "salary_year_avg": 0,

            "job_work_from_home": 0,

            "job_no_degree_mention": 0,

            "years_experience_proxy":
                len(profile.experience or ""),

            "job_title":
                profile.skills or "unknown",

            "job_location":
                "unknown",

            "job_country":
                "unknown"
        })

        ids.append(c.id)

    # =========================================
    # EMPTY CASE
    # =========================================
    if len(rows) == 0:

        clusters = {
            "senior": [],
            "intermediate": [],
            "junior": []
        }

        save_clusters(post_id, clusters)

        return clusters

    # =========================================
    # DATAFRAME
    # =========================================
    df = pd.DataFrame(rows)

    # =========================================
    # TRANSFORM
    # =========================================
    X = preprocessor.transform(df)

    # =========================================
    # PREDICT
    # =========================================
    if hasattr(model, "predict"):
        labels = model.predict(X)
    else:
        labels = model.fit_predict(X)

    # =========================================
    # BUILD CLUSTERS
    # =========================================
    clusters = {

        "senior": [],
        "intermediate": [],
        "junior": []
    }

    for i, label in enumerate(labels):

        # SIMPLE STATIC MAPPING
        if label == 0:
            clusters["junior"].append(ids[i])

        elif label == 1:
            clusters["intermediate"].append(ids[i])

        else:
            clusters["senior"].append(ids[i])

    # =========================================
    # SAVE FILE
    # =========================================
    save_clusters(post_id, clusters)

    return clusters