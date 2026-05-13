# Hugging Face Space — Docker
# Builds the same shim as services/scbe-shim, but as a FastAPI app
# suitable for HF Spaces free CPU tier.

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY shim ./shim

# HF Spaces injects PORT; default to 7860 for local docker run.
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
