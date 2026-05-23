FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn twilio \
    google-cloud-pubsub google-cloud-logging \
    google-cloud-secret-manager google-cloud-storage \
    langdetect httpx python-multipart

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
