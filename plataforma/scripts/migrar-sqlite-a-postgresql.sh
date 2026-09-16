#!/bin/bash
# Alias de postgresql-completo.sh (compatibilidad).
exec "$(dirname "$0")/postgresql-completo.sh" "$@"
