# Florence 프로젝트

Florence는 임산부를 위한 건강 정보 제공 서비스로, 대규모 언어 모델(LLM)을 활용하여 임신 관련 질문에 대한 정확하고 신뢰할 수 있는 정보를 제공합니다.

## 주요 기능

- 임신 주차별 정보 제공
- 임신 중 증상에 대한 정보 제공
- 임신 중 식이 관련 정보 제공
- 임신 중 검사 관련 정보 제공
- 임신 관련 복지 정보 제공
- 일반적인 임신 관련 질문에 대한 답변

## 시작하기

### 필수 조건

- Python 3.10 이상
- Django 4.2
- PostgreSQL 14 이상
- 기타 필요한 패키지 (requirements.txt 참조)

### 설치

1. 저장소 클론

```bash
git clone https://github.com/your-username/florence-project.git
cd florence-project
```

2. 가상 환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 의존성 설치

```bash
pip install -r requirements.txt
```

4. 환경 변수 설정

`.env` 파일을 프로젝트 루트 디렉토리에 생성하고 다음 변수를 설정합니다:

```
# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key

# Django 설정
SECRET_KEY=your_django_secret_key
DEBUG=True

# PostgreSQL 설정
DB_USER=your_db_username  # postgresql 아이디
DB_PASSWORD=your_db_password  # postgresql 비밀번호
DB_HOST=localhost
DB_PORT=5432
```

### 환경 변수 설정 방법

1. **VSCode에서 .env 파일 만들기**

   1. VSCode에서 프로젝트 폴더를 엽니다.
   2. 왼쪽 탐색기(Explorer) 패널에서 프로젝트 루트 디렉토리를 마우스 오른쪽 버튼으로 클릭합니다.
   3. 컨텍스트 메뉴에서 "새 파일(New File)"을 선택합니다.
   4. 파일 이름으로 `.env`를 입력하고 Enter 키를 누릅니다.
   5. 새로 생성된 .env 파일에 다음 내용을 입력합니다:
   
      ```
      # OpenAI API 설정
      OPENAI_API_KEY=your_openai_api_key
      
      # Django 설정
      SECRET_KEY=your_django_secret_key
      DEBUG=True
      
      # PostgreSQL 설정
      DB_USER=your_db_username  # postgresql 아이디
      DB_PASSWORD=your_db_password  # postgresql 비밀번호
      DB_HOST=localhost
      DB_PORT=5432
      ```

2. **OpenAI API 키 얻기**

   OpenAI API 키가 없는 경우:
   
   1. [OpenAI 웹사이트](https://platform.openai.com/)에 가입합니다.
   2. API 섹션으로 이동하여 새 API 키를 생성합니다.
   3. 생성된 키를 `.env` 파일의 `OPENAI_API_KEY` 변수에 설정합니다.

3. **Django SECRET_KEY 생성**

   새로운 Django SECRET_KEY를 생성하려면:



   출력된 값을 `.env` 파일의 `SECRET_KEY` 변수에 설정합니다.

### 데이터베이스 설정 (PostgreSQL)

1. PostgreSQL 설치

macOS:
```bash
brew install postgresql@14
```

Ubuntu:
```bash
sudo apt update
sudo apt install postgresql-14
```

Windows:
- PostgreSQL 공식 웹사이트에서 설치 프로그램을 다운로드하여 설치합니다.

2. PostgreSQL 서비스 시작

macOS:
```bash
brew services start postgresql@14
```

Ubuntu:
```bash
sudo systemctl start postgresql
```

Windows:
- 설치 과정에서 자동으로 서비스가 시작됩니다.

3. 데이터베이스 생성

```bash
createdb florence_db
```

4. **VSCode에서 PostgreSQL 확장 사용하기** (선택 사항)

   1. VSCode 왼쪽 사이드바에서 확장(Extensions) 아이콘을 클릭합니다.
   2. 검색창에 "PostgreSQL"을 입력합니다.
   3. "PostgreSQL" 확장을 찾아 설치합니다.
   4. 설치 후, 왼쪽 사이드바에서 PostgreSQL 아이콘을 클릭합니다.
   5. "+" 버튼을 클릭하여 새 연결을 추가합니다.
   6. 연결 정보를 입력합니다:
      - 호스트: localhost
      - 포트: 5432
      - 사용자: your_db_username
      - 비밀번호: your_db_password
      - 데이터베이스: florence_db
   7. "연결" 버튼을 클릭합니다.
   
   이제 VSCode에서 직접 데이터베이스를 관리할 수 있습니다.

5. 사용자 생성 및 권한 부여 (필요한 경우)

```bash
psql postgres
```

PostgreSQL 쉘에서:
```sql
CREATE USER your_username WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE florence_db TO your_username;
\q
```

### 문제 해결 (PostgreSQL)

1. **서비스 시작 오류**

   "Bootstrap failed: 5: Input/output error" 오류가 발생하는 경우:
   
   ```bash
   # PostgreSQL 서비스를 직접 실행
   /opt/homebrew/opt/postgresql@14/bin/postgres -D /opt/homebrew/var/postgresql@14
   ```
   
   또는 다음 명령으로 PostgreSQL 서비스를 재설치할 수 있습니다:
   
   ```bash
   brew uninstall --force postgresql
   brew install postgresql@14
   ```

2. **포트 충돌**

   "Address already in use" 오류가 발생하는 경우:
   
   ```bash
   # 현재 실행 중인 PostgreSQL 프로세스 확인
   ps aux | grep postgres
   
   # 해당 프로세스 종료
   kill <process_id>
   ```
   
   또는 다른 포트를 사용하도록 설정할 수 있습니다:
   
   ```bash
   # PostgreSQL 설정 파일 수정
   vim /opt/homebrew/var/postgresql@14/postgresql.conf
   
   # port = 5432 를 port = 5433 등으로 변경
   ```
   
   그리고 Django 설정에서도 포트를 변경합니다:
   
   ```python
   # config/settings.py
   DATABASES = {
       "default": {
           # ...
           "PORT": "5433",  # 변경된 포트
       }
   }
   ```

3. **Django 서버 포트 충돌**

   "Error: That port is already in use." 오류가 발생하는 경우:
   
   ```bash
   # 8000번 포트를 사용 중인 프로세스 확인
   lsof -i :8000
   
   # 해당 프로세스 종료
   kill <process_id>
   ```
   
   또는 다른 포트를 사용하여 서버를 실행할 수 있습니다:
   
   ```bash
   python manage.py runserver 8001
   ```

4. **VSCode에서 .env 파일이 보이지 않는 경우**

   .env 파일은 기본적으로 숨김 파일입니다. VSCode에서 숨김 파일을 표시하려면:
   
   1. VSCode 설정(Preferences)을 엽니다(Ctrl+, 또는 Cmd+,).
   2. 검색창에 "files.exclude"를 입력합니다.
   3. "Files: Exclude" 설정에서 "**/.env" 패턴이 있다면 제거합니다.
   4. 또는 "Files: Show Hidden" 설정을 활성화합니다.

5. **VSCode에서 PostgreSQL 확장 연결 오류**

   PostgreSQL 확장에서 연결 오류가 발생하는 경우:
   
   1. PostgreSQL 서비스가 실행 중인지 확인합니다.
   2. 연결 정보(사용자 이름, 비밀번호, 호스트, 포트)가 올바른지 확인합니다.
   3. 방화벽 설정을 확인합니다.
   4. PostgreSQL 로그 파일을 확인합니다:
      ```bash
      tail -f /opt/homebrew/var/postgresql@14/server.log
      ```

6. **UUID 관련 오류**

   SQLite에서 PostgreSQL로 전환하면 UUID 관련 오류가 해결됩니다. PostgreSQL은 UUID 데이터 타입을 네이티브로 지원합니다.
   
   UUID를 사용자 ID로 사용할 때 "Python int too large to convert to SQLite INTEGER" 오류가 발생하는 경우, PostgreSQL로 전환하면 해결됩니다.

### 마이그레이션 및 서버 실행

1. **데이터베이스 마이그레이션**

```bash
python manage.py migrate
```

2. **서버 실행**

```bash
python manage.py runserver
```

이제 `http://localhost:8000`에서 서버에 접속할 수 있습니다.

## API 사용 방법

자세한 API 사용 방법은 [LLM_API_GUIDE.md](LLM_API_GUIDE.md) 문서를 참조하세요.

### 예시 요청

```bash
curl -X POST http://localhost:8000/v1/sanitization/api/llm/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "8d58b7eb-a37e-4880-ac0e-32b766ffbcfa",
    "query_text": "임신 10주차에는 어떤 변화가 있나요?"
  }'
```

## 데모 시나리오

다양한 데모 시나리오는 [API_DEMO.md](API_DEMO.md) 문서를 참조하세요.

## 아키텍처

Florence 프로젝트의 아키텍처에 대한 자세한 내용은 [ARCHITECTURE.md](ARCHITECTURE.md) 문서를 참조하세요.

## 프로젝트 구조

```
florence-project/
├── accounts/              # 사용자 계정 관리 앱
├── config/                # 프로젝트 설정
├── rag/                   # 정보 검색 및 생성 앱
├── sanitization/          # 임신 관련 정보 제공 앱
├── static/                # 정적 파일
├── templates/             # HTML 템플릿
├── .env                   # 환경 변수
├── .gitignore             # Git 무시 파일
├── manage.py              # Django 관리 스크립트
├── requirements.txt       # 의존성 목록
└── README.md              # 이 파일
```

## 기여 방법

1. 이 저장소를 포크합니다.
2. 새 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`).
3. 변경 사항을 커밋합니다 (`git commit -m 'Add some amazing feature'`).
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`).
5. Pull Request를 생성합니다.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 연락처

프로젝트 관리자 - [이메일 주소](mailto:your-email@example.com)

프로젝트 링크: [https://github.com/your-username/florence-project](https://github.com/your-username/florence-project)

---

© 2025 Florence Project Team. All rights reserved.