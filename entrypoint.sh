#!/bin/bash
set -e

echo "🔄 Ожидание PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.5
done

echo "✅ PostgreSQL доступен"

echo "📦 Применение миграций..."
python manage.py migrate --noinput

echo "🧼 Сборка статики..."
python manage.py collectstatic --noinput

echo "🚀 Запуск Gunicorn..."
exec gunicorn src.wsgi:application --bind 0.0.0.0:8022 --workers=4 --threads=2 --worker-class=gthread
