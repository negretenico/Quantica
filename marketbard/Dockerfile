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

COPY marketbard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY marketbard/ .

RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

CMD ["python", "run.py"]
