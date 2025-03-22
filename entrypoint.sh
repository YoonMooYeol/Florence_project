#!/bin/bash

# PostgreSQL 서버 대기
if [ "$DATABASE" = "postgres" ]; then
    echo "PostgreSQL 서버 대기 중..."
    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL 서버 준비 완료"
fi

# 서비스 종류별 커맨드 (web 서비스에서만 마이그레이션 및 collectstatic 실행)
case "$SERVICE_TYPE" in
    "web")
        echo "Running manage.py makemigrations..."
        python manage.py makemigrations

        echo "Running migrate..."
        python manage.py migrate

        echo "Running collectstatic..."
        python manage.py collectstatic --noinput
        
        echo "Starting Gunicorn..."
        exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
        ;;
    "celery-worker")
        echo "Starting Celery Worker..."
        exec celery -A config worker -l info
        ;;
    "celery-beat")
        echo "Starting Celery Beat..."
        exec celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    *)
        exec "$@"
        ;;
esac