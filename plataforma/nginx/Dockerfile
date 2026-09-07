# Gateway único de la plataforma — compila la SPA unificada de React (Inventario +
# RBAC + Gestión de Riesgos nativo) en una etapa aparte, sin Node.js en runtime.
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY riesgos/frontend/src ../riesgos/frontend/src
ENV VITE_PLATAFORMA_UNIFICADA=1
ENV VITE_API_BASE_URL=/riesgos/api
ENV VITE_INVENTARIO_BASE_URL=/api
RUN npm run build

FROM nginx:1.27-alpine
# curl explícito (no asumido) para el healthcheck de docker-compose — evita
# depender de que la imagen base traiga wget/curl preinstalado, que varía
# entre versiones y no tenía forma de confirmar sin acceso a Docker.
RUN apk add --no-cache curl
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
# Build unificado con base "/" — interfaz principal en la raíz web.
COPY --from=frontend-build /frontend/dist /usr/share/nginx/html
