#!/bin/bash

# PostgreSQL 서버가 준비될 때까지 대기
if [ "$DATABASE" = "postgres" ]
then
    echo "PostgreSQL 서버 대기 중..."

    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL 서버 준비 완료"
fi

# 마이그레이션 실행
python manage.py migrate

# 정적 파일 수집
python manage.py collectstatic --no-input

# 서비스 종류에 따라 다른 명령어 실행
case "$SERVICE_TYPE" in
    "web")
        exec gunicorn config.wsgi:application --bind 0.0.0.0:8000
        ;;
    "celery-worker")
        exec celery -A config worker -l info
        ;;
    "celery-beat")
        exec celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    *)
        exec "$@"
        ;;
esac 