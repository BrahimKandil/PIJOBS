from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import pandas as pd

def train_cv_model(fileName):
    df = pd.read_csv(fileName)

    df["text"] = df["job_title"] + " " + df["job_skills"]

    # fake labels for training idea (replace with real dataset later)
    df["label"] = 1  # assume all accepted initially (as you said)

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(df["text"])
    y = df["label"]

    model = LogisticRegression()
    model.fit(X, y)

    pickle.dump(model, open("ml_models/cv_model.pkl", "wb"))
    pickle.dump(vectorizer, open("ml_models/cv_vectorizer.pkl", "wb"))