FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Render usa el CMD del Dockerfile (docker runtime no acepta startCommand).
# docker-compose sobreescribe este comando con runserver para desarrollo.
CMD sh -c "python manage.py migrate --noinput && python manage.py seed_demo && python manage.py collectstatic --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}"