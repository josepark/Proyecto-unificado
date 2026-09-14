#!/usr/bin/env bash
# Wrapper — use ./desplegar.sh para despliegue completo y verificado.
set -euo pipefail
cd "$(dirname "$0")/.."
exec ./desplegar.sh --purgar "$@"
