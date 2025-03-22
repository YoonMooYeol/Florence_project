FROM python:3.12-slim

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings

# 작업 디렉토리 생성
WORKDIR /app

# 시스템 종속성 + dos2unix 설치
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        netcat-traditional \
        gcc \
        python3-dev \
        libpq-dev \
        dos2unix \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 종속성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 코드 복사
COPY . /app

# entrypoint.sh 복사 및 권한 설정 (CRLF→LF 변환)
COPY entrypoint.sh /entrypoint.sh
RUN dos2unix /entrypoint.sh && chmod +x /entrypoint.sh

# 실행
ENTRYPOINT ["/entrypoint.sh"]