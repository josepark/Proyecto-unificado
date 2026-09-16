#!/bin/bash
# Crea la base suiin_rbac para la app Django rbac (Fase 1.1).
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
SELECT 'CREATE DATABASE suiin_rbac OWNER ${POSTGRES_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'suiin_rbac')\gexec
EOSQL
