FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

COPY --from=shared . /shared/
RUN pip install --no-cache-dir /shared/

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5001
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
