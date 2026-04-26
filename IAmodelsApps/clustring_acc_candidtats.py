from sklearn.cluster import KMeans
import pandas as pd
import pickle



def train_clustering(fileName):
    df = pd.read_csv(fileName)

    features = df[["salary_year_avg"]].fillna(0)

    kmeans = KMeans(n_clusters=3)
    kmeans.fit(features)

    df["cluster"] = kmeans.labels_

    pickle.dump(kmeans, open("ml_models/clustering.pkl", "wb"))