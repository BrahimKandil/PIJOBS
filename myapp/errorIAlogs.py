import os
from datetime import datetime
import traceback

def log_error(error, stage):
    # folder path (already exists, but safe to ensure)
    folder_path = "ml_models"
    os.makedirs(folder_path, exist_ok=True)

    # file path
    file_path = os.path.join(folder_path, "errors.txt")

    # check if file exists (optional but useful for logic clarity)
    file_exists = os.path.exists(file_path)

    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # mode explanation:
    # "a" = append (creates file if it doesn't exist)
    with open(file_path, "a", encoding="utf-8") as f:

        if not file_exists:
            f.write("===== ERROR LOG FILE CREATED =====\n\n")

        f.write(f"{date_str} => {stage} :\n")
        f.write(f"{str(error)}\n")
        f.write(traceback.format_exc())
        f.write("\n\n")