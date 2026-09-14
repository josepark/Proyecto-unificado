#!/bin/bash
# Verificación prioridad 1 — estabilidad sesión, proyectos y RBAC.
# Uso: ./scripts/verificar-prioridad-1.sh   (desde plataforma/)

set -euo pipefail

rojo() { printf '\033[0;31m%s\033[0m\n' "$*"; }
verde() { printf '\033[0;32m%s\033[0m\n' "$*"; }
amarillo() { printf '\033[0;33m%s\033[0m\n' "$*"; }

if [ ! -f docker-compose.yml ]; then
    rojo "Ejecute desde la raíz de plataforma/."
    exit 1
fi

FALLOS=0

echo "=== Prioridad 1 · Diagnóstico base ==="
if ! ./diagnostico_login.sh; then
    FALLOS=$((FALLOS + 1))
fi

echo ""
echo "=== Prioridad 1 · Login API (smoke, sin credenciales) ==="
codigo=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://127.0.0.1/api/auth/login/ 2>/dev/null || echo "000")
case "$codigo" in
    200) verde "POST/GET login endpoint accesible ($codigo)" ;;
    502|503|504|000) rojo "Login no accesible ($codigo)"; FALLOS=$((FALLOS + 1)) ;;
    *) amarillo "Login responde $codigo (revise si axes bloqueó la IP)" ;;
esac

echo ""
echo "=== Prioridad 1 · RBAC /api/resumen (vía nginx) ==="
if codigo=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://127.0.0.1/rbac/api/resumen 2>/dev/null); then
    case "$codigo" in
        200|401) verde "GET /rbac/api/resumen → $codigo (401 sin sesión es esperado)" ;;
        500) rojo "GET /rbac/api/resumen → 500 (rbac.db corrupta o vistas faltantes)"; FALLOS=$((FALLOS + 1)) ;;
        502|503|504) rojo "GET /rbac/api/resumen → $codigo (nginx/rbac caído)"; FALLOS=$((FALLOS + 1)) ;;
        *) amarillo "GET /rbac/api/resumen → $codigo" ;;
    esac
else
    rojo "Sin respuesta de /rbac/api/resumen"
    FALLOS=$((FALLOS + 1))
fi

echo ""
echo "=== Prioridad 1 · Checklist manual (navegador) ==="
cat <<'EOF'
Tras ./desplegar.sh --purgar:

  1. Entrar en http://localhost/login como admin
  2. Ir a Inventario → dashboard (activos cargan sin 403)
  3. Cambiar a Gestión de Riesgos y volver a Inventario
     → la cabecera debe seguir mostrando «Sesión: admin» (no «Iniciar sesión»)
  4. Cerrar sesión → debe ir a /login (sin 403 en consola en Inventario)
  5. Crear usuario de prueba en Inventario → Cuentas de acceso
     → al elegir Consultor/Dinamizador deben marcarse Inventario + RBAC
  6. Entrar como usuario nuevo → inventario vacío (espacio usuario-<login>)

Comprobar sesión en consola del navegador (F12):

  fetch('/api/sesion/', {credentials:'same-origin'}).then(r=>r.json()).then(console.log)

  Debe incluir: autenticado, modulos (p. ej. ["inventario","rbac"]), espacio_codigo
EOF

echo ""
if [ "$FALLOS" -eq 0 ]; then
    verde "Verificación automática prioridad 1: OK ($FALLOS fallos)"
    exit 0
fi

rojo "Verificación automática prioridad 1: $FALLOS chequeo(s) fallido(s)"
exit 1
