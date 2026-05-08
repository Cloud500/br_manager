# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.12
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./

ARG INSTALL_DEV=false
RUN --mount=type=cache,target=/root/.cache/uv \
    if [ "$INSTALL_DEV" = "true" ]; then \
        uv sync --frozen --group dev --no-install-project; \
    else \
        uv sync --frozen --no-dev --no-install-project; \
    fi

FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        fonts-dejavu-core \
        libffi8 \
        libharfbuzz0b \
        libjpeg62-turbo \
        libopenjp2-7 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libpq5 \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 django \
    && useradd --uid 10001 --gid django --create-home --shell /usr/sbin/nologin django \
    && mkdir -p /app/media /app/staticfiles /var/log/br_manager \
    && chown -R django:django /app /var/log/br_manager

COPY --from=builder --chown=django:django /opt/venv /opt/venv
COPY --chown=django:django . .
COPY --chmod=755 docker/entrypoint.sh /entrypoint.sh

RUN chown django:django /entrypoint.sh

USER django

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.asgi:application", "-k", "uvicorn_worker.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
