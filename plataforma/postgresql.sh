#!/bin/bash
# Atajo en la raíz de plataforma/ — ver scripts/postgresql-completo.sh
cd "$(dirname "$0")"
exec ./scripts/postgresql-completo.sh "$@"
