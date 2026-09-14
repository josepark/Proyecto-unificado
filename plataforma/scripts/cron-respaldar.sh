#!/bin/bash
# Respaldo unificado con código de salida para cron (falla si el tar no es válido).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p respaldos
exec python3 respaldar_plataforma.py
