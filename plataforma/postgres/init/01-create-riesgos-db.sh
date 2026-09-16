#!/bin/bash
# Crea la base suiin_riesgos (Inventario usa POSTGRES_DB=suiin_inventario).
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
SELECT 'CREATE DATABASE suiin_riesgos OWNER ${POSTGRES_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'suiin_riesgos')\gexec
EOSQL
