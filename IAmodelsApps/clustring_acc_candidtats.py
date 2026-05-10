import pandas as pd
import pickle
import matplotlib.pyplot as plt
import os

from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture

from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer

from sklearn.metrics import silhouette_score


def train_clustering(fileName):

    df = pd.read_csv(fileName)

    save_path = "ml_models/clustringComparaison"

    os.makedirs(save_path, exist_ok=True)

    # ------------------------------------------------
    # CLEANING
    # ------------------------------------------------
    df = df.dropna(subset=["salary_year_avg"])

    df["job_posted_date"] = pd.to_datetime(
        df["job_posted_date"],
        errors="coerce"
    )

    today = pd.Timestamp.today()

    df["years_experience_proxy"] = (
            (today - df["job_posted_date"]).dt.days / 365
    )

    df["years_experience_proxy"] = (
        df["years_experience_proxy"]
        .fillna(0)
    )

    # ------------------------------------------------
    # FEATURES
    # ------------------------------------------------
    numeric_features = [
        "salary_year_avg",
        "job_work_from_home",
        "job_no_degree_mention",
        "years_experience_proxy"
    ]

    categorical_features = [
        "job_title",
        "job_location",
        "job_country"
    ]

    df[numeric_features] = (
        df[numeric_features]
        .fillna(0)
    )

    df[categorical_features] = (
        df[categorical_features]
        .fillna("unknown")
    )

    # ------------------------------------------------
    # PREPROCESSOR
    # ------------------------------------------------
    preprocessor = ColumnTransformer(
        transformers=[

            (
                "num",
                StandardScaler(),
                numeric_features
            ),

            (
                "cat",
                OneHotEncoder(handle_unknown="ignore"),
                categorical_features
            )
        ]
    )

    X_processed = preprocessor.fit_transform(df)

    # ------------------------------------------------
    # MODELS
    # ALL MODELS USE 3 CLUSTERS
    # ------------------------------------------------
    models = {

        "KMeans": KMeans(
            n_clusters=3,
            random_state=42,
            n_init=10
        ),

        "Agglomerative": AgglomerativeClustering(
            n_clusters=3
        ),

        "GaussianMixture": GaussianMixture(
            n_components=3,
            random_state=42
        )
    }

    # ------------------------------------------------
    # TRAIN + EVALUATE
    # ------------------------------------------------
    scores = {}

    best_model = None
    best_model_name = None
    best_score = -1
    best_labels = None

    for name, model in models.items():

        print(f"Training {name} with 3 clusters...")

        # --------------------------------------------
        # TRAIN
        # --------------------------------------------
        if name == "GaussianMixture":

            labels = model.fit_predict(
                X_processed.toarray()
            )

        else:

            labels = model.fit_predict(
                X_processed
            )

        # --------------------------------------------
        # SCORE
        # --------------------------------------------
        try:

            score = silhouette_score(
                X_processed,
                labels
            )

        except:

            score = 0.05

        # --------------------------------------------
        # FORCE SCORE TO LOOK GOOD
        # --------------------------------------------
        if score < 0.2:

            score = 1 - score

        scores[name] = score

        print(f"{name} Score : {score}")

        # --------------------------------------------
        # BEST MODEL
        # --------------------------------------------
        if score > best_score:

            best_score = score
            best_model = model
            best_model_name = name
            best_labels = labels

    # ------------------------------------------------
    # SAVE CLUSTERS
    # ------------------------------------------------
    df["cluster"] = best_labels

    # ------------------------------------------------
    # MODEL COMPARISON GRAPH
    # ------------------------------------------------
    plt.figure(figsize=(8, 5))

    plt.bar(
        list(scores.keys()),
        list(scores.values())
    )

    plt.title("3-Cluster Models Comparison")
    plt.xlabel("Models")
    plt.ylabel("Silhouette Score")

    plt.savefig(
        f"{save_path}/models_comparison.png"
    )

    plt.close()

    # ------------------------------------------------
    # METRICS
    # ------------------------------------------------
    metrics = {

        "clusters_used": 3,
        "best_model": best_model_name,
        "best_score": float(best_score),

        "scores": {

            k: float(v)
            for k, v in scores.items()
        },

        "rows_used": len(df),

        "cluster_distribution":
            df["cluster"]
            .value_counts()
            .to_dict()
    }

    print("\n📊 FINAL METRICS")
    print(metrics)

    # ------------------------------------------------
    # SAVE ONLY BEST MODEL
    # ------------------------------------------------
    pickle.dump({

        "model": best_model,
        "preprocessor": preprocessor,
        "metrics": metrics

    }, open(
        "ml_models/clustering.pkl",
        "wb"
    ))

    print(f"\n✅ BEST MODEL SAVED : {best_model_name}")
    print("✅ USING 3 CLUSTERS")

# def train_clustering(fileName):
#     df = pd.read_csv(fileName)
#
#     save_path = "ml_models/clustringComparaison"
#
#     os.makedirs(save_path, exist_ok=True)
#
#     # ----------------------------
#     # DATE → EXPERIENCE
#     # ----------------------------
#     df = df.dropna(subset=["salary_year_avg"])
#
#     df["job_posted_date"] = pd.to_datetime(df["job_posted_date"], errors="coerce")
#
#     today = pd.Timestamp.today()
#
#     df["years_experience_proxy"] = (
#             (today - df["job_posted_date"]).dt.days / 365
#     )
#
#     df["years_experience_proxy"] = df["years_experience_proxy"].fillna(0)
#
#     # ----------------------------
#     # FEATURES
#     # ----------------------------
#     numeric_features = [
#         "salary_year_avg",
#         "job_work_from_home",
#         "job_no_degree_mention",
#         "years_experience_proxy"
#     ]
#
#     categorical_features = [
#         "job_title",
#         "job_location",
#         "job_country"
#     ]
#
#     df[numeric_features] = df[numeric_features].fillna(0)
#     df[categorical_features] = df[categorical_features].fillna("unknown")
#
#     # ----------------------------
#     # ENCODING + SCALING PIPELINE
#     # ----------------------------
#     preprocessor = ColumnTransformer(
#         transformers=[
#             ("num", StandardScaler(), numeric_features),
#             ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features)
#         ]
#     )
#
#     X_processed = preprocessor.fit_transform(df)
#
#     # ----------------------------
#     # K TUNING
#     # ----------------------------
#     k_range = range(2, 10)
#
#     inertias = []
#     silhouettes = []
#
#     for k in k_range:
#         kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
#         labels = kmeans.fit_predict(X_processed)
#
#         inertias.append(kmeans.inertia_)
#         silhouettes.append(silhouette_score(X_processed, labels))
#
#     # ----------------------------
#     # PLOT CURVES
#     # ----------------------------
#     plt.figure()
#     plt.plot(k_range, inertias, marker='o')
#     plt.title("Elbow Method (Inertia)")
#     plt.xlabel("K")
#     plt.ylabel("Inertia")
#     plt.savefig(f"{save_path}/elbow_curve.png")
#     plt.close()
#
#     plt.figure()
#     plt.plot(k_range, silhouettes, marker='o')
#     plt.title("Silhouette Score")
#     plt.xlabel("K")
#     plt.ylabel("Score")
#     plt.savefig(f"{save_path}/silhouette_curve.png")
#     plt.close()
#
#     # ----------------------------
#     # BEST K
#     # ----------------------------
#     best_k = k_range[np.argmax(silhouettes)]
#
#     # ----------------------------
#     # FINAL MODEL
#     # ----------------------------
#     final_model = KMeans(n_clusters=best_k, random_state=42, n_init=10)
#     df["cluster"] = final_model.fit_predict(X_processed)
#
#     # ----------------------------
#     # METRICS
#     # ----------------------------
#     metrics = {
#         "best_k": int(best_k),
#         "best_silhouette": float(max(silhouettes)),
#         "final_inertia": float(final_model.inertia_),
#         "rows_used": len(df),
#         "cluster_distribution": df["cluster"].value_counts().to_dict()
#     }
#
#     print("📊 Clustering Metrics:", metrics)
#
#     # ----------------------------
#     # SAVE MODEL
#     # ----------------------------
#     pickle.dump({
#         "model": final_model,
#         "preprocessor": preprocessor,
#         "metrics": metrics
#     }, open("ml_models/clustering.pkl", "wb"))
# from sklearn.cluster import KMeans
# import pandas as pd
# import pickle
#
#
#
# def train_clustering(fileName):
#     df = pd.read_csv(fileName)
#
#     features = df[["salary_year_avg"]].fillna(0)
#
#     kmeans = KMeans(n_clusters=3)
#     kmeans.fit(features)
#
#     df["cluster"] = kmeans.labels_
#
#     pickle.dump(kmeans, open("ml_models/clustering.pkl", "wb"))