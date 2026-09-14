# Task Force Présidentielle — backend production image.
#
# One image serves every AWS container option (App Runner, ECS/Fargate,
# Elastic Beanstalk on Docker), so the hosting choice can change later
# without rebuilding this file.

FROM python:3.13-slim

# Fail fast and log straight through to CloudWatch rather than buffering.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Pillow needs libjpeg/zlib at runtime; psycopg2-binary ships its own libpq.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libjpeg62-turbo \
        zlib1g \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first, so a code change does not reinstall the whole stack.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Baked into the image so no container start pays for it, and so a missing
# static file breaks the build rather than production. DEBUG/SECRET_KEY are
# build-time throwaways: settings.py refuses the placeholder key only when
# DEBUG is False, and nothing here touches the database.
RUN DEBUG=True SECRET_KEY=build-only python manage.py collectstatic --noinput

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 taskforce \
    && chown -R taskforce:taskforce /app
USER taskforce

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/healthz/" || exit 1

# Migrations run here rather than in a separate release step because App
# Runner has no release phase. Django migrations take a lock, so parallel
# instances serialise instead of colliding.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers ${GUNICORN_WORKERS:-3} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - --error-logfile -"]
