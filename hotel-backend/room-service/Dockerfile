# syntax=docker/dockerfile:1.7
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
# install OS tools including curl (used by healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p uploads
EXPOSE 5002
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5002", "--workers", "3", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
