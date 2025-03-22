#!/bin/bash

# PostgreSQL 서버 대기 (더욱 Robust하게 연결 확인)
if [ "$DATABASE" = "postgres" ]; then
    echo "PostgreSQL 서버 대기 시작..."
    until PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q'; do
      sleep 1
      echo "PostgreSQL 연결 재시도..."
    done
    echo "PostgreSQL 서버 연결 성공"
fi

# 서비스 종류별 커맨드 (web 서비스에서만 마이그레이션 및 collectstatic 실행)
case "$SERVICE_TYPE" in
    "web")
        echo "Running manage.py makemigrations..."
        python manage.py makemigrations --noinput # --noinput 추가 (비대화형 모드)

        echo "Running migrate..."
        python manage.py migrate --noinput # --noinput 추가 (비대화형 모드)
        if [ $? -ne 0 ]; then # 마이그레이션 실패 시 에러 로그 출력 후 exit
          echo "Error: Django migrations failed!"
          python manage.py migrate --traceback # --traceback 추가 (자세한 에러 정보 출력)
          exit 1
        fi

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