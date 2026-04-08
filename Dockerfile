FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Bangkok

RUN apt-get update \
    && apt-get install -y --no-install-recommends cron tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN sed -i 's/\r$//' /app/run-sync.sh /app/docker-entrypoint.sh /app/crontab \
    && chmod +x /app/run-sync.sh /app/docker-entrypoint.sh \
    && crontab /app/crontab

CMD ["sh", "/app/docker-entrypoint.sh"]
