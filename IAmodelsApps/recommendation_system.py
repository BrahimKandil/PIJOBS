import sys
import subprocess
import pandas as pd
import pickle
import os


# ----------------------------
# AUTO INSTALL DEPENDENCIES
# ----------------------------
def install_if_missing(package, import_name=None):
    try:
        if import_name:
            __import__(import_name)
        else:
            __import__(package)
    except ImportError:
        print(f"📦 Installing missing package: {package}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])


install_if_missing("sentence-transformers", "sentence_transformers")
install_if_missing("torch", "torch")
install_if_missing("psutil", "psutil")


from sentence_transformers import SentenceTransformer
import torch as torch
import psutil

device = "cuda" if torch.cuda.is_available() else "cpu"
print("🔥 Using device:", device)

def train_recommender(fileName):
    df = pd.read_csv(fileName)

    # ----------------------------
    # 1. BUILD TEXT REPRESENTATION
    # ----------------------------
    df["text"] = (
            df["job_title_short"].fillna("") + " " +
            df["job_title"].fillna("") + " " +
            df["job_location"].fillna("") + " " +
            df["job_schedule_type"].fillna("") + " " +
            df["job_country"].fillna("") + " " +
            df["job_skills"].fillna("") + " " +
            df["job_type_skills"].fillna("") + " " +
            df["job_no_degree_mention"].astype(str)
    )

    # ----------------------------
    # 2. LOAD DEEP LEARNING MODEL
    # ----------------------------
    model = SentenceTransformer("all-MiniLM-L6-v2",device=device)

    # ----------------------------
    # 3. CREATE EMBEDDINGS
    # ----------------------------
    embeddings = model.encode(
        df["text"].tolist(),
        batch_size=64,
        show_progress_bar=True
    )

    # ----------------------------
    # 4. SAVE EVERYTHING IN ONE FILE
    # ----------------------------
    recommender_bundle = {
        "model": model,
        "embeddings": embeddings,
        "data": df
    }

    pickle.dump(recommender_bundle, open("ml_models/recommender.pkl", "wb"))



# def train_recommender(fileName):
#     df = pd.read_csv(fileName)
#
#     df["text"] = df["job_title"] + " " + df["job_skills"]
#
#     vectorizer = TfidfVectorizer(stop_words="english")
#     matrix = vectorizer.fit_transform(df["text"])
#
#     similarity = cosine_similarity(matrix)
#
#     # save
#     pickle.dump(vectorizer, open("ml_models/vectorizer.pkl", "wb"))
#     pickle.dump(similarity, open("ml_models/recommender.pkl", "wb"))
#     pickle.dump(df, open("ml_models/jobs_df.pkl", "wb"))