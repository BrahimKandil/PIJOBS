import streamlit as st
import subprocess
import sys
import os
import django
import time
import requests

# ==========================================
# ADD PROJECT PATH
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# ==========================================
# DJANGO SETTINGS
# ==========================================

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "pijobs.settings"   # replace with YOUR project name
)

django.setup()

# ==========================================
# START DJANGO SERVER
# ==========================================

@st.cache_resource
def start_django_backend():
    try:
        requests.get("http://127.0.0.1:8000", timeout=2)
        return None

    except:
        process = subprocess.Popen(
            [
                sys.executable,
                "manage.py",
                "runserver",
                "127.0.0.1:8000"
            ]
        )

        time.sleep(3)

        return process


django_process = start_django_backend()

# ==========================================
# UI
# ==========================================

st.title("💼 PIJOBS Dashboard")

st.success("Django + Streamlit connected successfully")
