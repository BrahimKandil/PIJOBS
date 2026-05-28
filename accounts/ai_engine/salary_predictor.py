import pickle
import pandas as pd
import numpy as np

from IAmodelsApps.features_pipeline import build_features


MODEL_PATH = "ml_models/salary_model.pkl"
def predict_salary(candidature):

    import numpy as np
    import pandas as pd
    import pickle

    MODEL_PATH = "ml_models/salary_model.pkl"

    # ==========================
    # LOAD MODEL ARTIFACTS
    # ==========================
    saved = pickle.load(open(MODEL_PATH, "rb"))

    model = saved["model"]
    encoders = saved["label_encoders"]
    template = saved["template_row"].copy()

    # ==========================
    # EXTRACT SKILLS
    # ==========================
    skills = candidature.post.required_skills

    if skills:
        skills = [s.strip().lower() for s in skills.split(",")]
    else:
        skills = []

    # ==========================
    # OVERWRITE TEMPLATE VALUES
    # ==========================
    template["job_title_short"] = candidature.post.title
    template["company_name"] = candidature.post.company_name
    template["job_country"] = "Tunisia"
    template["job_work_from_home"] = 0
    template["job_no_degree_mention"] = 0
    template["job_schedule_type"] = "full time"

    # ==========================
    # ENGINEERED FEATURES
    # ==========================
    template["seniority"] = 1
    template["skill_count"] = len(skills)

    high_value = {"aws", "gcp", "azure", "spark", "kubernetes", "tensorflow", "pytorch"}

    template["high_value_skill_score"] = sum(
        1 for s in skills if s in high_value
    )

    # ==========================
    # LABEL ENCODING (SAFE)
    # ==========================
    for col in template.columns:
        if col in encoders:
            le = encoders[col]
            template[col] = template[col].astype(str).apply(
                lambda x: le.transform([x])[0] if x in le.classes_ else -1
            )

    # ==========================
    # CRITICAL FIX: FORCE NUMERIC
    # ==========================
    template = template.apply(pd.to_numeric, errors="coerce").fillna(0)

    # ==========================
    # ALIGN WITH TRAINING FEATURES
    # ==========================
    template = template.reindex(
        columns=model.get_booster().feature_names,
        fill_value=0
    )

    # ==========================
    # PREDICTION
    # ==========================
    pred_log = model.predict(template)[0]
    salary = np.expm1(pred_log)
    if salary < 0 or salary < 500 :
        salary = 500
    return round(float(salary), 2)