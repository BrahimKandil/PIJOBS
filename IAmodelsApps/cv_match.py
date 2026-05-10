from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import pandas as pd
import pandas as pd
import numpy as np
import pickle
import os
import re

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import classification_report
from sklearn.pipeline import Pipeline


def create_situation(company_name):

    company_name = str(company_name).strip()

    if len(company_name) > 0 and company_name[0].isdigit():
        return "rejected"

    return "accepted"


def train_cv_model(fileName):

    # -------------------------
    # LOAD DATA
    # -------------------------
    df = pd.read_csv(fileName)

    # -------------------------
    # KEEP IMPORTANT COLUMNS
    # -------------------------
    columns_needed = [
        "job_title_short",
        "job_title",
        "job_location",
        "search_location",
        "job_country",
        "company_name",
        "job_health_insurance",
        "job_schedule_type",
        "job_work_from_home",
        "job_type_skills",
        "job_skills"
    ]

    df = df[columns_needed]

    # -------------------------
    # CLEAN NULLS
    # -------------------------
    df = df.fillna("")

    # -------------------------
    # CREATE TARGET
    # -------------------------
    df["situation"] = df["company_name"].apply(create_situation)

    # -------------------------
    # COMBINE FEATURES
    # -------------------------
    df["text"] = (
            df["job_title_short"].astype(str) + " " +
            df["job_title"].astype(str) + " " +
            df["job_location"].astype(str) + " " +
            df["search_location"].astype(str) + " " +
            df["job_country"].astype(str) + " " +
            df["company_name"].astype(str) + " " +
            df["job_health_insurance"].astype(str) + " " +
            df["job_schedule_type"].astype(str) + " " +
            df["job_work_from_home"].astype(str) + " " +
            df["job_type_skills"].astype(str) + " " +
            df["job_skills"].astype(str)
    )

    # -------------------------
    # FEATURES / TARGET
    # -------------------------
    X = df["text"]
    y = df["situation"]

    # -------------------------
    # SPLIT
    # -------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    # -------------------------
    # PIPELINE
    # -------------------------
    model = Pipeline([

        (
            "tfidf",
            TfidfVectorizer(
                stop_words="english",
                max_features=10000,
                ngram_range=(1, 2)
            )
        ),

        (
            "classifier",
            MLPClassifier(
                hidden_layer_sizes=(128, 64),
                max_iter=20,
                random_state=42,
                verbose=True
            )
        )
    ])

    # -------------------------
    # TRAIN
    # -------------------------
    model.fit(X_train, y_train)

    # -------------------------
    # TEST
    # -------------------------
    predictions = model.predict(X_test)

    print(classification_report(y_test, predictions))

    # -------------------------
    # SAVE
    # -------------------------
    os.makedirs("ml_models", exist_ok=True)

    pickle.dump(
        model,
        open("ml_models/cv_matching_model.pkl", "wb")
    )

    print("Model trained and saved successfully")

# def train_cv_model(fileName):
#     df = pd.read_csv(fileName)
#
#     df["text"] = df["job_title"] + " " + df["job_skills"]
#
#     # fake labels for training idea (replace with real dataset later)
#     df["label"] = 1  # assume all accepted initially (as you said)
#
#     vectorizer = TfidfVectorizer()
#     X = vectorizer.fit_transform(df["text"])
#     y = df["label"]
#
#     model = LogisticRegression()
#     model.fit(X, y)
#
#     pickle.dump(model, open("ml_models/cv_model.pkl", "wb"))
#     pickle.dump(vectorizer, open("ml_models/cv_vectorizer.pkl", "wb"))