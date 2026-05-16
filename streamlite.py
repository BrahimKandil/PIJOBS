import subprocess
import sys
import os
import time

def run_django():
    """Starts the Django development server."""
    print("🚀 Starting Django Backend...")
    # Using sys.executable ensures it uses your current virtual environment's Python
    return subprocess.Popen([sys.executable, "manage.py", "runserver", "127.0.0.1:8000"])

def run_streamlit():
    """Starts the Streamlit frontend."""
    print("🎨 Starting Streamlit Frontend...")
    # Runs streamlit run against itself, passing a special flag to prevent an infinite loop
    return subprocess.Popen([sys.executable, "-m", "streamlit", "run", __file__, "--", "is_child"])

if __name__ == "__main__":
    # Check if this script is being executed by the Streamlit subprocess
    if "is_child" in sys.argv:
        # --- YOUR ACTUAL STREAMLIT UI CODE GOES HERE ---
        import streamlit as st
        import django
        
        # Initialize Django configuration inside the Streamlit worker
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pijobs_django.settings")
        django.setup()
        
        # Example UI
        st.title("💼 PIJOBS Unified Dashboard")
        st.write("Django backend and Streamlit UI are now running together!")
        
    else:
        # This is the main orchestrator block
        django_process = None
        streamlit_process = None
        try:
            # 1. Start Django
            django_process = run_django()
            time.sleep(2)  # Give Django a brief moment to boot up
            
            # 2. Start Streamlit
            streamlit_process = run_streamlit()
            
            # Keep the main process alive while children run
            django_process.wait()
            streamlit_process.wait()
            
        except KeyboardInterrupt:
            print("\n🛑 Shutting down both servers gracefully...")
            if django_process:
                django_process.terminate()
            if streamlit_process:
                streamlit_process.terminate()
