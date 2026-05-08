#!/bin/sh
set -eu

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

if [ "${DJANGO_WAIT_FOR_DB:-1}" = "1" ]; then
    python manage.py wait_for_database --timeout "${DB_WAIT_TIMEOUT:-60}"
fi

if [ "${DJANGO_MIGRATE:-1}" = "1" ]; then
    python manage.py migrate --noinput
fi

if [ "${DJANGO_SEED_TESTDATA:-0}" = "1" ]; then
    python manage.py seed_testdata_once --config "${DJANGO_SEED_TESTDATA_CONFIG:-testdata_config_small.json}"
fi

if [ "${DJANGO_COLLECTSTATIC:-0}" = "1" ]; then
    python manage.py collectstatic --noinput
fi

if [ -n "${ROOT_USER_EMAIL:-}" ] || [ -n "${ROOT_USER_PASSWORD:-}" ]; then
    python manage.py ensure_root_user
fi

exec "$@"
