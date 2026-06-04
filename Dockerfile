# Base Python image (Downgraded to 3.11 to ensure binary wheels exist for your heavy ML stack)
FROM python:3.11-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# =========================
# SYSTEM DEPENDENCIES
# =========================
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    unzip \
    gnupg2 \
    ca-certificates \
    apt-transport-https \
    gcc \
    g++ \
    unixodbc \
    unixodbc-dev \
    cargo \
    rustc \
    && rm -rf /var/lib/apt/lists/*

# =========================
# MICROSOFT ODBC DRIVER
# =========================
RUN mkdir -p /etc/apt/keyrings

RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor > /etc/apt/keyrings/microsoft.gpg

RUN echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
    > /etc/apt/sources.list.d/mssql-release.list

RUN apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# =========================
# DOWNLOAD ML MODELS
# =========================
RUN mkdir -p /app/ml_models
# Install gdown to bypass Google Drive's virus scan confirmation page safely
RUN pip install --no-cache-dir gdown

# Download using gdown via the file ID directly
RUN gdown 1vXtOXOE7MHF2BGvNYpNBAz8oz5zf3gBJ -O /tmp/models.zip

# Unzip into ml_models directory
RUN unzip /tmp/models.zip -d /app/ml_models && \
    rm /tmp/models.zip

# =========================
# PYTHON DEPENDENCIES
# =========================
COPY requirements.txt .

# Upgrade pip and install all requirements cleanly
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Explicitly install the ultra-lightweight CPU version of Torch inside the container image
RUN pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cpu --no-cache-dir

# =========================
# PROJECT FILES
# =========================
COPY . .

# =========================
# EXPOSE PORT
# =========================
EXPOSE 8000

# =========================
# START COMMAND (Production Ready Gunicorn)
# =========================
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--pythonpath", "/app", "config.wsgi:application"]
# # Base Python image
# FROM python:3.13-slim

# # Prevent Python from writing .pyc files
# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# # Set work directory
# WORKDIR /app

# # =========================
# # SYSTEM DEPENDENCIES
# # =========================
# RUN apt-get update && apt-get install -y \
#     curl \
#     wget \
#     unzip \
#     gnupg2 \
#     ca-certificates \
#     apt-transport-https \
#     gcc \
#     g++ \
#     unixodbc \
#     unixodbc-dev \
#     && rm -rf /var/lib/apt/lists/*

# # =========================
# # MICROSOFT ODBC DRIVER
# # =========================

# RUN mkdir -p /etc/apt/keyrings

# RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
#     | gpg --dearmor > /etc/apt/keyrings/microsoft.gpg

# RUN echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
#     > /etc/apt/sources.list.d/mssql-release.list

# RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
#     && rm -rf /var/lib/apt/lists/*

# # =========================
# # DOWNLOAD ML MODELS
# # =========================

# RUN mkdir -p /app/ml_models

# # Download ZIP from Google Drive
# RUN wget --no-check-certificate \
#     "https://drive.google.com/uc?export=download&id=1vXtOXOE7MHF2BGvNYpNBAz8oz5zf3gBJ" \
#     -O /tmp/models.zip

# # Unzip into ml_models directory
# RUN unzip /tmp/models.zip -d /app/ml_models && \
#     rm /tmp/models.zip

# # =========================
# # PYTHON DEPENDENCIES
# # =========================
# COPY requirements.txt .

# RUN pip install --upgrade pip && \
#     pip install -r requirements.txt

# # =========================
# # PROJECT FILES
# # =========================
# COPY . .

# # =========================
# # EXPOSE PORT
# # =========================
# EXPOSE 8000

# # =========================
# # START COMMAND
# # =========================
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
# # # Base Python image
# # FROM python:3.13-slim

# # # Prevent Python from writing .pyc files
# # ENV PYTHONDONTWRITEBYTECODE=1
# # ENV PYTHONUNBUFFERED=1

# # # Set work directory
# # WORKDIR /app

# # # =========================
# # # SYSTEM DEPENDENCIES
# # # =========================
# # RUN apt-get update && apt-get install -y \
# #     curl \
# #     gnupg2 \
# #     ca-certificates \
# #     apt-transport-https \
# #     gcc \
# #     g++ \
# #     unixodbc \
# #     unixodbc-dev \
# #     && rm -rf /var/lib/apt/lists/*

# # # =========================
# # # MICROSOFT ODBC DRIVER (FIXED MODERN WAY)
# # # =========================

# # RUN mkdir -p /etc/apt/keyrings

# # RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
# #     | gpg --dearmor > /etc/apt/keyrings/microsoft.gpg

# # RUN echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
# #     > /etc/apt/sources.list.d/mssql-release.list

# # RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
# #     && rm -rf /var/lib/apt/lists/*

# # # =========================
# # # PYTHON DEPENDENCIES
# # # =========================
# # COPY requirements.txt .

# # RUN pip install --upgrade pip && \
# #     pip install -r requirements.txt

# # # =========================
# # # PROJECT FILES
# # # =========================
# # COPY . .

# # # =========================
# # # EXPOSE PORT
# # # =========================
# # EXPOSE 8000

# # # =========================
# # # START COMMAND
# # # =========================
# # CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
