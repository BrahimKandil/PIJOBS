import streamlit as st
import subprocess
import sys
import os
import django
import time
import requests

# ======================================================
# 1. GET CURRENT DIRECTORY
# ======================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Add project root to Python path
sys.path.append(BASE_DIR)

# ======================================================
# 2. DEBUG PROJECT STRUCTURE
# ======================================================

st.write("📁 Project files/folders:")
st.write(os.listdir(BASE_DIR))

# ======================================================
# 3. CHANGE THIS TO YOUR DJANGO PROJECT FOLDER
# ======================================================
# IMPORTANT:
# Replace "YOUR_PROJECT_FOLDER"
# with the folder containing settings.py
#
# Example:
# if you have:
# mysite/settings.py
#
# then write:
# "mysite.settings"
# ======================================================

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "YOUR_PROJECT_FOLDER.settings"
)

# ======================================================
# 4. INITIALIZE DJANGO
# ======================================================

try:
    django.setup()
    st.success("✅ Django initialized successfully")

except Exception as e:
    st.error("❌ Django setup failed")
    st.exception(e)

# ======================================================
# 5. START DJANGO SERVER
# ======================================================

@st.cache_resource
def start_django_backend():

    try:
        # Check if server already running
        requests.get("http://127.0.0.1:8000", timeout=2)

        st.info("✅ Django server already running")
        return None

    except:

        st.info("🚀 Starting Django backend server...")

        process = subprocess.Popen(
            [
                sys.executable,
                "manage.py",
                "runserver",
                "127.0.0.1:8000"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        time.sleep(5)

        return process


django_process = start_django_backend()

# ======================================================
# 6. STREAMLIT UI
# ======================================================

st.title("💼 PIJOBS Dashboard")

st.success("✅ Streamlit + Django connected")

st.write("You can now use Django ORM inside Streamlit.")

# ======================================================
# 7. EXAMPLE DJANGO IMPORT
# ======================================================

# Example:
#
# from myapp.models import User
#
# users = User.objects.all()
#
# st.write(users)
