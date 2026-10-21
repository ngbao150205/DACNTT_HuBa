FROM python:3.12-slim

WORKDIR /app/crawler-service

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY crawler-service/requirements.txt /app/crawler-service/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 10001 crawler \
    && useradd --uid 10001 --gid crawler --create-home crawler \
    && mkdir -p /var/lib/crawler \
    && chown crawler:crawler /var/lib/crawler

COPY crawler-service /app/crawler-service

USER crawler

EXPOSE 8002

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
