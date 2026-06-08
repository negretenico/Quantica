FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/lists/*

COPY shared/ /shared/
RUN pip install --no-cache-dir /shared/

COPY marketanalysis/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY marketanalysis/ .

RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

CMD ["python", "run.py"]
