#!/bin/bash

# PostgreSQL 서버 대기
if [ "$DATABASE" = "postgres" ]; then
    echo "PostgreSQL 서버 대기 중..."
    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL 서버 준비 완료"
fi

# (마이그레이션, collectstatic은 EB .ebextensions에서 처리 가능)
# 또는 여기에서 해도 되지만 EB의 leader_only 컨테이너에서 처리할 때는 주의.

# 서비스 종류별 커맨드
case "$SERVICE_TYPE" in
    "web")
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


sudo docker exec -it current-web-1 pip install Pillow
sudo docker exec -it current-web-1 python manage.py migrate