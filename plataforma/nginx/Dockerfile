# Gateway único de la plataforma — ahora también compila el frontend de
# React (Fase 2 de la migración, README sección 9) en una etapa aparte,
# para no necesitar Node.js en la imagen final que sirve el tráfico.
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# SUIIN-SGSI-RIESGOS (gestión de riesgos y plan de tratamiento) — mismo patrón
# que el frontend de arriba: se compila aparte y se sirve bajo /riesgos/,
# con la API apuntando a esa misma ruta relativa (mismo origen, sin CORS).
FROM node:20-slim AS riesgos-frontend-build
WORKDIR /riesgos-frontend
COPY riesgos/frontend/package.json riesgos/frontend/package-lock.json ./
RUN npm ci
COPY riesgos/frontend/ ./
ENV VITE_BASE_PATH=/riesgos/
ENV VITE_API_BASE_URL=/riesgos/api
# El Inventario vive en la raíz de este mismo origen (mismo dominio, mismo
# nginx) — ruta absoluta, no relativa a /riesgos/, para el intento de sesión
# única (ver riesgos/frontend/src/context/AuthContext.jsx).
ENV VITE_INVENTARIO_BASE_URL=/api
RUN npm run build

FROM nginx:1.27-alpine
# curl explícito (no asumido) para el healthcheck de docker-compose — evita
# depender de que la imagen base traiga wget/curl preinstalado, que varía
# entre versiones y no tenía forma de confirmar sin acceso a Docker.
RUN apk add --no-cache curl
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
# Build de Vite con base "/" — interfaz principal en la raíz web.
COPY --from=frontend-build /frontend/dist /usr/share/nginx/html
COPY --from=riesgos-frontend-build /riesgos-frontend/dist /usr/share/nginx/html/riesgos
