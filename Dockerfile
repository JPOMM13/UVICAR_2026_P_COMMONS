# Usar una imagen base ligera de Python
FROM python:3.11-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar los requerimientos e instalarlos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente de la aplicación
COPY listSims/app_sims.py .

# Crear un directorio para la caché con permisos adecuados
RUN mkdir -p /app/data && chmod 777 /app/data
ENV CACHE_PATH=/app/data/sims_cache.json

# Exponer el puerto que usa Flask
EXPOSE 5001

# Comando para ejecutar la aplicación usando Gunicorn para producción
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--threads", "4", "--timeout", "60", "app_sims:app"]
