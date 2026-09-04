#!/bin/bash
# SUIIN-RBAC — arranque de producción con gunicorn (4 procesos).
# Sirva detrás de nginx con TLS; active SESSION_COOKIE_SECURE en app.py.
export SUIIN_RBAC_SECRET="${SUIIN_RBAC_SECRET:?Defina SUIIN_RBAC_SECRET}"
exec gunicorn --workers 4 --bind 127.0.0.1:5000 \
     --access-logfile - --error-logfile - app:app
