#!/bin/bash
# Alias de reparar-login.sh (solo arregla 401, sin re-migrar).
exec "$(dirname "$0")/reparar-login.sh" "$@"
