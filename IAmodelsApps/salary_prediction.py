from sklearn.ensemble import RandomForestRegressor
import pandas as pd
import pickle

def train_salary_model(fileName):
    df = pd.read_csv(fileName)

    X = df[["job_no_degree_mention"]].fillna(0)
    y = df["salary_year_avg"].fillna(0)

    model = RandomForestRegressor()
    model.fit(X, y)

    pickle.dump(model, open("ml_models/salary_model.pkl", "wb"))