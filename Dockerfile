FROM python:3.13.16-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=5000 \
    APP_VERSION=1.0.0 \
    DATABASE_PATH=/data/lume.sqlite3

WORKDIR /srv/lume

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 lume \
    && useradd --uid 10001 --gid lume --no-create-home --shell /usr/sbin/nologin lume \
    && mkdir -p /data \
    && chown lume:lume /data \
    && chmod 0700 /data

# Deliberately copy runtime sources only, never the host instance/ or .env.
COPY app.py database.py gunicorn.conf.py ./
COPY app/ ./app/
COPY docker/healthcheck.py ./docker/healthcheck.py

USER 10001:10001
EXPOSE 5000
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "/srv/lume/docker/healthcheck.py"]

CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:create_app()"]
