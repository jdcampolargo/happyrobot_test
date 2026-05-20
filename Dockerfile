FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    API_KEY=local-dev-key \
    DATABASE_PATH=/app/data/app.db

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data
COPY templates ./templates
COPY static ./static

RUN mkdir -p /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os,urllib.request; req=urllib.request.Request('http://localhost:8000/health', headers={'X-API-Key': os.environ.get('API_KEY','local-dev-key')}); urllib.request.urlopen(req, timeout=5)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
