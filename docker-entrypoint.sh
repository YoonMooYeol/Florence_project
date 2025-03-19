#!/bin/bash
set -e

# 마이그레이션 실행 (배포 시점에 한 번만 실행되도록 구성)
python manage.py migrate --noinput

# static 파일 수집 (필요한 경우 활성화)
# python manage.py collectstatic --noinput

# Gunicorn 서버 실행
gunicorn config.wsgi:application --bind 0.0.0.0:8000