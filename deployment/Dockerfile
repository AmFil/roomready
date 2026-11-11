FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY app/requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY app/app.py app/identity.py app/storage.py ./
COPY app/templates/index.html templates/
USER 10001:10001
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn --no-control-socket --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 30 app:app"]
