FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

# Genera los estáticos dentro de la imagen; en el contenedor, docker-compose
# monta un volumen sobre STATIC_ROOT que nginx lee directamente.
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Aplica migraciones pendientes en cada arranque (idempotente: no afecta la
# base de datos ya poblada que trae el proyecto) y luego levanta gunicorn.
# SQLite no admite escrituras concurrentes desde varios workers de
# gunicorn; mantener --workers 1 hasta migrar a PostgreSQL.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1 --access-logfile - --error-logfile -"]
