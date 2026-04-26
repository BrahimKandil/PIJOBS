import os

import traceback

from IAmodelsApps.clustring_acc_candidtats import train_clustering
from IAmodelsApps.cv_match import train_cv_model
from IAmodelsApps.recommendation_system import train_recommender
from IAmodelsApps.salary_prediction import train_salary_model
from myapp.errorIAlogs import log_error
from myapp.startup_loader import export_datawarehouse_to_csv

MODEL_PATHS = {
    "recommender": "ml_models/recommender.pkl",
    "cv_model": "ml_models/cv_model.pkl",
    "clustering": "ml_models/clustering.pkl",
    "salary": "ml_models/salary_model.pkl"
}
fileName = "data/full_jobs_dataset.csv"
def model_exists(path):
    return os.path.exists(path)

def run_pipeline():
    try:
        print("🚀 Step 1: Exporting CSV...")

        success = export_datawarehouse_to_csv()

        if not success:
            print("❌ CSV export failed. STOP pipeline.")
            return

        print("✅ CSV ready. Starting ML training...")

        # =========================
        # MODEL 1 - RECOMMENDER
        # =========================
        try:
            if model_exists(MODEL_PATHS["recommender"]):
                print("📁 Recommender already exists → skipping training")
            else:
                print("📊 Training recommender...")
                train_recommender(fileName)
                print("✅ Recommender done")
        except Exception as e:
            print("⚠️ Recommender failed:", e)
            log_error(e, "train_recommender()")
            traceback.print_exc()

        # =========================
        # MODEL 2 - CV NLP
        # =========================
        try:
            if model_exists(MODEL_PATHS["cv_model"]):
                print("🧠 CV model already exists → skipping training")
            else:
                print("🧠 Training CV model...")
                train_cv_model(fileName)
                print("✅ CV model done")

        except Exception as e:
            print("⚠️ CV model failed:", e)
            log_error(e, "train_cv_model()")

        traceback.print_exc()

        # =========================
        # MODEL 3 - CLUSTERING
        # =========================
        try:
            if model_exists(MODEL_PATHS["clustering"]):
                print("📦 Clustering model already exists → skipping training")
            else:
                print("📦 Training clustering...")
                train_clustering(fileName)
                print("✅ Clustering done")
        except Exception as e:
            print("⚠️ Clustering failed:", e)
            log_error(e, "train_clustering()")
            traceback.print_exc()

        # =========================
        # MODEL 4 - REGRESSION
        # =========================
        try:
            if model_exists(MODEL_PATHS["salary"]):
                print("💰 Salary model already exists → skipping training")
            else:
                print("💰 Training salary model...")
                train_salary_model(fileName)
                print("✅ Salary model done")
        except Exception as e:
            print("⚠️ Salary model failed:", e)
            log_error(e, "train_salary_model()")
            traceback.print_exc()

        print("🎉 Pipeline finished")

    except Exception as e:
        print("❌ Critical failure (CSV stage):", e)
        traceback.print_exc()