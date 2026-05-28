import pickle

# ==========================================
# LOAD MODEL
# ==========================================

model = pickle.load(
    open(
        "ml_models/cv_matching_model.pkl",
        "rb"
    )
)


# ==========================================
# PREDICT SITUATION
# ==========================================

def predict_candidature_situation(text):

    prediction = model.predict([text])[0]

    return prediction