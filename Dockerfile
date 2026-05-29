# Base Python image
FROM python:3.13-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# =========================
# SYSTEM DEPENDENCIES
# =========================
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    ca-certificates \
    apt-transport-https \
    gcc \
    g++ \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# =========================
# MICROSOFT ODBC DRIVER (FIXED MODERN WAY)
# =========================

RUN mkdir -p /etc/apt/keyrings

RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor > /etc/apt/keyrings/microsoft.gpg

RUN echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
    > /etc/apt/sources.list.d/mssql-release.list

RUN apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# =========================
# PYTHON DEPENDENCIES
# =========================
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# =========================
# PROJECT FILES
# =========================
COPY . .

# =========================
# EXPOSE PORT
# =========================
EXPOSE 8000

# =========================
# START COMMAND
# =========================
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
