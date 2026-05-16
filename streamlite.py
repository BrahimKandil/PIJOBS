import streamlit as st
import subprocess
import sys
import os
import django

# ==========================================
# 1. START DJANGO SERVER (Runs exactly once)
# ==========================================
@st.cache_resource
def start_django_backend():
    print("🚀 Starting Django Backend Server...")
    # This fires up the Django server as a background process
    process = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "127.0.0.1:8000"],
        stdout=subprocess.DEVNULL, # Suppress clutter in your terminal logs
        stderr=subprocess.DEVNULL
    )
    return process

# Trigger the background process initialization
django_process = start_django_backend()


# ==========================================
# 2. CONNECT TO DJANGO ORM
# ==========================================
# Set up Django configuration so your models can communicate with the database
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pijobs_django.settings")
django.setup()


# ==========================================
# 3. YOUR STREAMLIT UI CODE
# ==========================================
st.title("💼 PIJOBS Unified Dashboard")
st.success("Django backend server and Streamlit UI are up and running!")

st.write("Now you can fetch data, write queries using your Django models, or import your views directly right here.")
