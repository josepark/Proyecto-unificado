#!/bin/sh
set -eu

python manage.py migrate --noinput

if [ "${DJANGO_DB_ENGINE:-}" = "postgresql" ]; then
  python manage.py asegurar_bases_postgresql
  python manage.py migrate rbac --database=rbac --noinput
  python manage.py inicializar_rbac
fi

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-1}" \
  --access-logfile - \
  --error-logfile -
