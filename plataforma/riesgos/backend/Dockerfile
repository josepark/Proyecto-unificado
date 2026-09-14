FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Igual que inventario: aplica migraciones pendientes en cada arranque
# (idempotente — no afecta la base de datos ya poblada que trae el proyecto,
# incluido el catálogo de 93 controles ISO 27001) y luego levanta gunicorn.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn suiin_riesgos_config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --access-logfile - --error-logfile -"]
