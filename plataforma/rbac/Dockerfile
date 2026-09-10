FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copia de referencia para recuperar rbac.db corrupta (volumen montado puede dañarla).
RUN cp rbac.db rbac.db.referencia

EXPOSE 5000

# Si el volumen montado no trae rbac.db (primer arranque en un entorno nuevo,
# sin la base de datos ya poblada), se crea con seed.py antes de servir.
CMD ["sh", "-c", "test -f rbac.db || python3 seed.py; python3 recuperar_rbac_db.py; python3 migrar_espacio_datos.py; exec gunicorn app:app --bind 0.0.0.0:5000 --workers 4 --access-logfile - --error-logfile -"]
