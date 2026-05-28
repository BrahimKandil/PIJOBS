from IAmodelsApps.features_pipeline import build_features
import os
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from xgboost import XGBRegressor


# -------------------------
# SAVE PLOT
# -------------------------
def save_plot(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()


# -------------------------
# LABEL ENCODING FUNCTION
# -------------------------
def label_encode_dataframe(X_train, X_test, save_path=None):

    encoders = {}

    X_train = X_train.copy()
    X_test = X_test.copy()

    for col in X_train.columns:

        if X_train[col].dtype == "object":

            le = LabelEncoder()

            # fit ONLY train
            le.fit(X_train[col].astype(str))

            X_train[col] = le.transform(X_train[col].astype(str))

            # handle unseen labels in test
            X_test[col] = X_test[col].astype(str).apply(
                lambda x: le.transform([x])[0] if x in le.classes_ else -1
            )

            encoders[col] = le

    # 🚨 IMPORTANT: ensure ALL columns are numeric BEFORE model
    X_train = X_train.apply(pd.to_numeric, errors="coerce").fillna(0)
    X_test = X_test.apply(pd.to_numeric, errors="coerce").fillna(0)

    # DO NOT force astype(float32 yet (XGBoost handles it)

    if save_path:
        os.makedirs(save_path, exist_ok=True)
        with open(os.path.join(save_path, "label_encoders.pkl"), "wb") as f:
            pickle.dump(encoders, f)

    return X_train, X_test, encoders

# -------------------------
# TRAIN FUNCTION
# -------------------------
def train_salary_models(fileName):

    save_path = "ml_models/salaryComparaison"
    os.makedirs(save_path, exist_ok=True)

    df = pd.read_csv(fileName)

    # =========================================================
    # 0. CLEAN DATA (STRICT ALIGNMENT FIX)
    # =========================================================
    df = df.dropna(subset=["salary_year_avg"])
    df = df[df["salary_year_avg"] <= df["salary_year_avg"].quantile(0.99)]
    df = df.reset_index(drop=True)

    # =========================================================
    # 1. FEATURES
    # =========================================================
    X, y, skill_encoder = build_features(df)

    X = X.reset_index(drop=True)
    y = np.log1p(y).reset_index(drop=True)

    # =========================================================
    # 2. FEATURE ENGINEERING (SAFE + ALIGNED)
    # =========================================================

    X["seniority"] = df["job_title_short"].astype(str).apply(
        lambda x: 3 if any(k in x.lower() for k in ["senior", "sr", "lead", "principal"])
        else 2 if any(k in x.lower() for k in ["mid", "intermediate"])
        else 1
    )

    X["skill_count"] = df["job_skills"].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )

    high_value = {"aws", "gcp", "azure", "spark", "kubernetes", "tensorflow", "pytorch"}

    X["high_value_skill_score"] = df["job_skills"].apply(
        lambda skills: sum(1 for s in skills if s in high_value)
        if isinstance(skills, list) else 0
    )

    # =========================================================
    # 3. FIXED SPLIT (NO df.index ANYMORE 🚨)
    # =========================================================
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42
    )

    # =========================================================
    # 4. SAFE TARGET ENCODING (NO INDEX BUG)
    # =========================================================
    train_df = df.iloc[X_train.index].reset_index(drop=True)
    test_df = df.iloc[X_test.index].reset_index(drop=True)

    company_mean = train_df.groupby("company_name")["salary_year_avg"].mean()
    country_mean = train_df.groupby("job_country")["salary_year_avg"].mean()

    X_train = X_train.copy()
    X_test = X_test.copy()

    X_train["company_name"] = train_df["company_name"].map(company_mean)
    X_test["company_name"] = test_df["company_name"].map(company_mean)

    X_train["job_country"] = train_df["job_country"].map(country_mean)
    X_test["job_country"] = test_df["job_country"].map(country_mean)

    # fill missing values
    X_train = X_train.fillna(company_mean.mean())
    X_test = X_test.fillna(company_mean.mean())

    # =========================================================
    # 5. LABEL ENCODING
    # =========================================================
    X_train, X_test, encoders = label_encode_dataframe(
        X_train, X_test,
        save_path=save_path
    )

    # =========================================================
    # 6. MODELS
    # =========================================================
    models = {
        "XGBoost": XGBRegressor(
            n_estimators=2500,
            learning_rate=0.02,
            max_depth=7,
            subsample=0.85,
            colsample_bytree=0.85,
            min_child_weight=3,
            reg_alpha=0.1,
            reg_lambda=1.0,
            gamma=0.1,
            tree_method="hist",
            random_state=42,
            n_jobs=-1
        ),

        "RandomForest": RandomForestRegressor(
            n_estimators=800,
            max_depth=20,
            min_samples_leaf=2,
            max_features="sqrt",
            random_state=42,
            n_jobs=-1
        ),
        "Ridge": Ridge(alpha=1.0)
    }

    # =========================================================
    # 7. TRAIN
    # =========================================================
    results = {}
    trained_models = {}

    for name, model in models.items():

        print(f"🚀 Training {name}")

        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        preds_real = np.expm1(preds)
        y_real = np.expm1(y_test)

        mae = mean_absolute_error(y_real, preds_real)
        r2 = 1-r2_score(y_real, preds_real)

        results[name] = {"MAE": mae, "R2": r2}
        trained_models[name] = model

        print(f"✅ {name} → R2: {r2:.4f}")

    # =========================================================
    # 8. SAVE BEST MODEL
    # =========================================================
    best = max(results, key=lambda x: results[x]["R2"])
    template_row = X.iloc[[0]].copy()

    pickle.dump({
        "model": trained_models[best],
        "metrics": results,
        "best_model": best,
        "skill_encoder": skill_encoder,
        "label_encoders": encoders,
        "template_row": template_row
    }, open("ml_models/salary_model.pkl", "wb"))

    print(f"\n🏆 BEST MODEL: {best}")#
