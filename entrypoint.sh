#!/bin/bash

# PostgreSQL 서버 대기
if [ "$DATABASE" = "postgres" ]; then
    echo "PostgreSQL 서버 대기 중..."
    
    # DB_HOST와 RDS_HOSTNAME 둘 다 고려
    DB_HOST_VAR=${RDS_HOSTNAME:-$DB_HOST}
    DB_PORT_VAR=${RDS_PORT:-$DB_PORT}
    
    echo "DB 호스트: $DB_HOST_VAR, DB 포트: $DB_PORT_VAR"
    
    while ! nc -z $DB_HOST_VAR $DB_PORT_VAR; do
      sleep 0.1
    done
    echo "PostgreSQL 서버 준비 완료"
fi

# (마이그레이션, collectstatic은 EB .ebextensions에서 처리 가능)
# 또는 여기에서 해도 되지만 EB의 leader_only 컨테이너에서 처리할 때는 주의.

# 서비스 종류별 커맨드
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
        echo "Running migrate for django_celery_beat..."
        python manage.py migrate django_celery_beat
        
        echo "Starting Celery Beat..."
        exec celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    *)
        exec "$@"
        ;;
esac