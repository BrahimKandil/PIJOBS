import os
import json
import pickle
from datetime import datetime

def log_all_models_status():
    folder_path = "ml_models"
    os.makedirs(folder_path, exist_ok=True)

    log_file = os.path.join(folder_path, "models_status.txt")
    file_exists = os.path.exists(log_file)

    models = [f for f in os.listdir(folder_path) if f.endswith(".pkl")]

    log_entry = {
        "models_found": [],
        "total_models": len(models)
    }

    for model_file in models:
        model_path = os.path.join(folder_path, model_file)

        metrics = {}

        # ----------------------------
        # TRY READ METRICS FROM PKL
        # ----------------------------
        try:
            with open(model_path, "rb") as f:
                data = pickle.load(f)

                # if model saved as dict (model + metrics)
                if isinstance(data, dict) and "metrics" in data:
                    metrics = data["metrics"]

        except Exception:
            metrics = {"error": "cannot read model"}

        model_info = {
            "model_name": model_file,
            "size_kb": round(os.path.getsize(model_path) / 1024, 2),
            "status": "READY",
            "metrics": metrics if metrics else "N/A"
        }

        log_entry["models_found"].append(model_info)

    # write log
    with open(log_file, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write("===== MODEL GLOBAL STATUS LOG CREATED =====\n\n")
        f.write("===== "+ datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" =====\n")
        f.write(json.dumps(log_entry, indent=4))
        f.write("\n\n")