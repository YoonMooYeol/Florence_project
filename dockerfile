FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y gcc

COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY . /app/

# (선택 사항) 필요한 경우 빌드 단계에서 static 파일 수집 (권장하지 않음)
# RUN python manage.py collectstatic --noinput

EXPOSE 8000

# docker-entrypoint.sh 스크립트 실행
CMD ["/app/docker-entrypoint.sh"]