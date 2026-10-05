FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY dashboard/requirements.txt dashboard/requirements.txt
RUN pip install --no-cache-dir -r dashboard/requirements.txt

COPY dashboard/ dashboard/
COPY datos/mgn2018_municipios_atlantico.geojson datos/mgn2018_municipios_atlantico.geojson

EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn --chdir dashboard app:server --bind 0.0.0.0:${PORT} --workers 2 --timeout 120"]
