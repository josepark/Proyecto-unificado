#!/bin/bash
# Prueba POST /api/auth/login/ vía nginx (mismo flujo que la SPA).
# Uso: source scripts/lib/probar-login-nginx.sh && probar_login_nginx

probar_login_nginx() {
    local usuario="${1:-admin}"
    local clave="${2:-SUIIN2026#}"
    local url_base="${3:-http://127.0.0.1}"
    local jar codigo csrf cuerpo

    jar=$(mktemp)
    cuerpo=$(mktemp)
    trap 'rm -f "$jar" "$cuerpo"' RETURN

    if ! curl -sf -c "$jar" -b "$jar" "${url_base}/api/auth/login/" >/dev/null; then
        echo "GET ${url_base}/api/auth/login/ sin respuesta — ¿nginx arriba?" >&2
        return 1
    fi

    csrf=$(grep -E '[[:space:]]csrftoken[[:space:]]' "$jar" 2>/dev/null | tail -1 | awk '{print $7}')
    if [ -z "$csrf" ]; then
        echo "No se obtuvo cookie csrftoken — revise nginx → inventario" >&2
        return 1
    fi

    codigo=$(curl -s -o "$cuerpo" -w '%{http_code}' \
        -b "$jar" -c "$jar" \
        -X POST "${url_base}/api/auth/login/" \
        -H "Content-Type: application/json" \
        -H "X-CSRFToken: ${csrf}" \
        -d "{\"username\":\"${usuario}\",\"password\":\"${clave}\"}")

    if [ "$codigo" = "200" ]; then
        echo "POST ${url_base}/api/auth/login/ → 200 (${usuario})"
        return 0
    fi

    echo "POST ${url_base}/api/auth/login/ → ${codigo}" >&2
    head -c 400 "$cuerpo" >&2 || true
    echo >&2
    return 1
}
