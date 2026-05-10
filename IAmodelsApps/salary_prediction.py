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

    pickle.dump({
        "model": trained_models[best],
        "metrics": results,
        "best_model": best,
        "skill_encoder": skill_encoder,
        "label_encoders": encoders
    }, open("ml_models/salary_model.pkl", "wb"))

    print(f"\n🏆 BEST MODEL: {best}")#
#     # -------------------------
#     # BUILD FEATURES
#     # -------------------------
#     X, y, skill_encoder = build_features(df)
#
#     X = X.reset_index(drop=True)
#     y = y.reset_index(drop=True)
#
#
#
#     X = X.drop(columns=['job_id',
#                     'job_title',
#                     'job_location',
#                     'search_location',
#                     'job_type_skills',
#                     'job_skills',
#                     'job_via',
#                     'job_posted_date',
#                     'salary_rate',
#                     'salary_year_avg',
#                     'salary_hour_avg'], inplace=True, errors="ignore")
#
#     # -------------------------
#     # FINAL ENCODING FOR STRINGS
#     # -------------------------
#     cat_cols = X.select_dtypes(include=["object"]).columns
#     num_cols = X.select_dtypes(exclude=["object"]).columns
#
#     preprocessor = ColumnTransformer([
#         ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)
#     ], remainder="passthrough")
#
#     # -------------------------
#     # SPLIT
#     # -------------------------
#     X_train, X_test, y_train, y_test = train_test_split(
#         X, y, test_size=0.2, random_state=42
#     )
#
#     # apply encoding
#     X_train = preprocessor.fit_transform(X_train)
#     X_test = preprocessor.transform(X_test)
#     # -------------------------
#     # MODELS
#     # -------------------------
#     models = {
#         "RandomForest": RandomForestRegressor(
#             n_estimators=800,
#             max_depth=18,
#             min_samples_leaf=8,
#             max_features="sqrt",
#             random_state=42,
#             n_jobs=-1
#         ),
#
#         "XGBoost": XGBRegressor(
#             n_estimators=3000,
#             learning_rate=0.02,
#             max_depth=5,
#             subsample=0.8,
#             colsample_bytree=0.7,
#             min_child_weight=3,
#             gamma=0.1,
#             reg_alpha=0.1,
#             reg_lambda=1.0,
#             tree_method="hist",
#             random_state=42,
#             n_jobs=-1
#         ),
#
#         "Ridge": Ridge(alpha=1.0)
#     }
#     results = {}
#     trained_models = {}
#
#     # -------------------------
#     # TRAIN LOOP
#     # -------------------------
#     for name, model in models.items():
#
#         print(f"🚀 Training {name}")
#
#         model.fit(X_train, y_train)
#         preds = model.predict(X_test)
#
#         mae = mean_absolute_error(y_test, preds)
#         r2 = r2_score(y_test, preds)
#
#         results[name] = {"MAE": float(mae), "R2": float(r2)}
#         trained_models[name] = model
#
#         print(f"✅ {name} → R2: {r2:.4f}")
#
#     # -------------------------
#     # RESULTS
#     # -------------------------
#     print("\n📊 FINAL RESULTS:")
#     for name, m in results.items():
#         print(f"{name} → R2: {m['R2']:.4f} | MAE: {m['MAE']:.2f}")
#
#     # -------------------------
#     # PLOTS
#     # -------------------------
#     names = list(results.keys())
#     r2 = [results[n]["R2"] for n in names]
#     mae = [results[n]["MAE"] for n in names]
#
#     plt.figure()
#     plt.bar(names, r2)
#     plt.title("R2 Comparison")
#     plt.savefig(f"{save_path}/r2.png")
#     plt.close()
#
#     plt.figure()
#     plt.bar(names, mae)
#     plt.title("MAE Comparison")
#     plt.savefig(f"{save_path}/mae.png")
#     plt.close()
#
#     # -------------------------
#     # SAVE BEST MODEL
#     # -------------------------
#     best = max(results, key=lambda x: results[x]["R2"])
#
#     pickle.dump({
#         "model": trained_models[best],
#         "preprocessor": preprocessor,
#         "metrics": results,
#         "best_model": best,
#         "skill_encoder": skill_encoder
#     }, open("ml_models/salary_model.pkl", "wb"))
#
#     print(f"\n🏆 Best Model: {best}")# import pickle
# import matplotlib.pyplot as plt
#
# from concurrent.futures import ThreadPoolExecutor
#
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import mean_absolute_error, r2_score
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.linear_model import LinearRegression
#
# from xgboost import XGBRegressor
#
#
# def train_salary_models(fileName):
#     import os
#     save_path = "ml_models/salaryComparaison"
#
#     os.makedirs(save_path, exist_ok=True)
#     df = pd.read_csv(fileName)
#
#     # ----------------------------
#     # CLEAN DATA
#     # ----------------------------
#     df = df.dropna(subset=["salary_year_avg"])
#
#     y = df["salary_year_avg"]
#
#     # ----------------------------
#     # FEATURES
#     # ----------------------------
#     features = [
#         'job_title',
#         'job_title_short',
#         'job_location',
#         'job_via',
#         'job_schedule_type',
#         'job_work_from_home',
#         'job_no_degree_mention',
#         'job_country',
#         'company_name',
#         'job_skills',
#         'job_type_skills'
#     ]
#
#     X = df[features].fillna("unknown")
#
#     # ----------------------------
#     # ONE HOT ENCODING
#     # ----------------------------
#     preprocessor = ColumnTransformer(
#         transformers=[
#             ("cat", OneHotEncoder(handle_unknown="ignore"), features)
#         ]
#     )
#
#     X_encoded = preprocessor.fit_transform(X)
#
#     # ----------------------------
#     # SPLIT
#     # ----------------------------
#     X_train, X_test, y_train, y_test = train_test_split(
#         X_encoded, y, test_size=0.2, random_state=42
#     )
#
#     # ----------------------------
#     # MODELS
#     # ----------------------------
#     models = {
#         "RandomForest": RandomForestRegressor(
#             n_estimators=150,
#             n_jobs=-1,
#             random_state=42
#         ),
#         "XGBoost": XGBRegressor(
#             n_estimators=1000,
#             learning_rate=0.05,
#             max_depth=8,
#             subsample=0.8,
#             colsample_bytree=0.8,
#             tree_method="hist",
#             random_state=42
#         ),
#         "LinearRegression": LinearRegression()
#     }
#
#     results = {}
#
#     # ----------------------------
#     # TRAIN FUNCTION (THREAD SAFE)
#     # ----------------------------
#     def train_model(name, model):
#         print(f"🚀 Training {name}...")
#
#         model.fit(X_train, y_train)
#
#         y_pred = model.predict(X_test)
#
#         mae = mean_absolute_error(y_test, y_pred)
#         r2 = r2_score(y_test, y_pred)
#
#         results[name] = {
#             "MAE": float(mae),
#             "R2": float(r2)
#         }
#
#         print(f"✅ {name} done → R2: {r2:.4f}")
#
#         return name, model
#
#     # ----------------------------
#     # PARALLEL TRAINING
#     # ----------------------------
#     trained_models = {}
#
#     with ThreadPoolExecutor(max_workers=3) as executor:
#         futures = []
#
#         for name, model in models.items():
#             futures.append(executor.submit(train_model, name, model))
#
#         for future in futures:
#             name, model = future.result()
#             trained_models[name] = model
#
#     # ----------------------------
#     # PRINT RESULTS
#     # ----------------------------
#     print("\n📊 FINAL RESULTS:")
#     for name, metric in results.items():
#         print(f"{name} → R2: {metric['R2']:.4f} | MAE: {metric['MAE']:.2f}")
#
#     # ----------------------------
#     # PLOT COMPARISON
#     # ----------------------------
#     model_names = list(results.keys())
#     r2_scores = [results[m]["R2"] for m in model_names]
#     mae_scores = [results[m]["MAE"] for m in model_names]
#
#     plt.figure()
#
#     plt.bar(model_names, r2_scores)
#     plt.title("Model Comparison - R2 Score")
#     plt.xlabel("Model")
#     plt.ylabel("R2 Score")
#
#     for i, v in enumerate(r2_scores):
#         plt.text(i, v, f"{v:.2f}", ha='center')
#     plt.savefig(f"{save_path}/model_r2_comparison.png")
#
#     plt.close()
#
#     plt.figure()
#
#     plt.bar(model_names, mae_scores)
#     plt.title("Model Comparison - MAE")
#     plt.xlabel("Model")
#     plt.ylabel("MAE")
#
#     for i, v in enumerate(mae_scores):
#         plt.text(i, v, f"{v:.0f}", ha='center')
#
#     plt.savefig(f"{save_path}/model_mae_comparison.png")
#     plt.close()
#
#     # ----------------------------
#     # SAVE BEST MODEL
#     # ----------------------------
#     best_model_name = max(results, key=lambda x: results[x]["R2"])
#
#     pickle.dump({
#         "model": trained_models[best_model_name],
#         "preprocessor": preprocessor,
#         "metrics": results,
#         "best_model": best_model_name
#     }, open("ml_models/salary_model.pkl", "wb"))
#
#     print(f"\n🏆 Best Model: {best_model_name}")