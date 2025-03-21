# Florence Project

## 목차
- [프로젝트 소개](#프로젝트-소개)
- [기술 스택](#기술-스택)
- [설치 및 설정](#설치-및-설정)
- [실행 방법](#실행-방법)
- [프로젝트 구조](#프로젝트-구조)
- [API 가이드](#api-가이드)

## 프로젝트 개요

---

 Florence 프로젝트는 Django 백엔드와 Vue.js 3 프론트엔드를 사용하는 웹 애플리케이션입니다. 

이 프로젝트는 LangChain과 OpenAI를 활용한 AI 기능을 포함하고 있습니다.

## 기술 스택 (Tech Stack)

---

### 웹 서버

- **Django** (버전 4.2): 웹 애플리케이션 개발 프레임워크
- **Gunicorn**: WSGI 서버로 Django 애플리케이션 실행
- **Nginx**: 리버스 프록시 서버, 정적 파일 제공

### 웹 개발

- **Django REST Framework** (버전 3.15.2): RESTful API 구축을 위한 Django 라이브러리

### 비동기 작업

- **Celery**: 비동기 작업 처리 라이브러리
- **Celery Beat**: 주기적인 작업 스케줄링

### 메시지 브로커

- **Redis**: Celery의 메시지 브로커로 사용

### 데이터베이스

- **PostgreSQL**: 관계형 데이터베이스 관리 시스템
- **ChromaDB**: 벡터 데이터베이스, AI 모델을 위한 데이터 저장 및 검색 처리

### 배포

- **Docker**: 애플리케이션 컨테이너화
- **Docker Compose**: 멀티 컨테이너 Docker 애플리케이션 관리
- **AWS Elastic Beanstalk**: 애플리케이션 배포 및 관리

### 인증

- **JWT 인증 (djangorestframework-simplejwt)**: API 인증을 위한 JWT 사용

### AI / 자연어 처리 관련 기술

- **LangChain**: LangChain을 활용한 자연어 처리 및 AI 기반 기능 통합
- **OpenAI**: GPT와 같은 OpenAI 모델 통합

## 로컬 개발 환경 설정

---

### 사전 요구사항

- Docker 및 Docker Compose 설치
- Python 3.8 이상 설치

### 환경 변수 설정

1. `.env.example` 파일을 `.env`로 복사
2. `.env` 파일의 환경 변수 값을 적절히 수정

### 로컬 실행 방법

```bash
# Docker Compose로 모든 서비스 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f
```

## AWS Elastic Beanstalk 배포 방법

---

### 사전 요구사항

- AWS CLI 설치
- EB CLI 설치
- AWS 계정 및 적절한 권한 설정

### 배포 단계

1. EB CLI 초기화

```bash
eb init

```

1. 환경 생성

```bash
eb create florence-env --single --instance-type t2.small

```

1. 배포

```bash
eb deploy

```

1. 환경 변수 설정

```bash
eb setenv SECRET_KEY=your-secret-key DB_NAME=florence_db DB_USER=florence_user DB_PASSWORD=your-password

```

## 유지보수

---

### 데이터베이스 백업

AWS RDS를 사용할 경우 자동 백업 설정을 권장합니다.

### 로그 확인

```bash
eb logs

```

### 모니터링

AWS CloudWatch를 통해 시스템 모니터링을 설정할 수 있습니다.

## 문제 해결

---

### 일반적인 문제

1. 데이터베이스 연결 오류 - 보안 그룹 및 네트워크 설정 확인
2. 정적 파일 접근 불가 - collectstatic 명령 실행 및 S3 버킷 권한 확인

### 지원 및 문의

문제가 발생할 경우 프로젝트 관리자에게 문의하세요.

## 설치 및 설정

---

### 사전 요구사항

- Python 3.11 이상
- PostgreSQL

### 백엔드 설정

- 저장소 클론

```bash
git clone <https://github.com/yourusername/Florence_project.git>
cd Florence_project

```

- 가상 환경 생성 및 활성화

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

```

- 의존성 설치

```bash
pip install -r requirements.txt

```

- 환경 변수 설정 (.env 파일 생성)

```
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:password@localhost:5432/florence_db
OPENAI_API_KEY=your_openai_api_key

```

- 데이터베이스 마이그레이션

```bash
python manage.py migrate

```

### 실행방법

---

```bash
python manage.py runserver 0.0.0.0:8000
```

## 프로젝트 구조

---

```
Florence_project/
├── backend/                  # 백엔드 디렉토리
│   ├── config/               # 프로젝트 설정
│   ├── api/                  # API 앱
│   ├── users/                # 사용자 관리 앱
│   ├── ai_services/          # AI 관련 서비스
│   └── manage.py             # Django 관리 스크립트
├── frontend/                 # 프론트엔드 디렉토리
│   ├── public/               # 정적 파일
│   ├── src/                  # Vue 소스 코드
│   │   ├── assets/           # 이미지, 폰트 등
│   │   ├── components/       # Vue 컴포넌트
│   │   ├── views/            # 페이지 컴포넌트
│   │   ├── router/           # Vue Router 설정
│   │   ├── store/            # Vuex/Pinia 상태 관리
│   │   ├── services/         # API 호출 서비스
│   │   ├── App.vue           # 루트 컴포넌트
│   │   └── main.js           # 진입점
│   └── package.json          # npm 설정
├── .env                      # 환경 변수
├── .gitignore                # Git 제외 파일
└── requirements.txt          # Python 의존성

```

# API 가이드

---

## 기본 정보

- 기본 URL: `http://localhost:8000/api/`
- 모든 요청과 응답은 JSON 형식입니다
- 인증이 필요한 엔드포인트는 JWT 토큰을 사용합니다

## 인증

### 로그인

- **URL**: `/api/auth/token/`
- **Method**: `POST`
- **설명**: 사용자 인증 및 JWT 토큰 발급
- **요청 예시**:

```json
{
    "username": "사용자이름",
    "password": "비밀번호"
}

```

- **응답 예시**:

```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

```

### 토큰 갱신

- **URL**: `/api/auth/token/refresh/`
- **Method**: `POST`
- **설명**: 만료된 액세스 토큰 갱신
- **요청 예시**:

```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

```

- **응답 예시**:

```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}

```

## 사용자 관리

### 사용자 등록

- **URL**: `/api/users/register/`
- **Method**: `POST`
- **설명**: 새 사용자 등록
- **요청 예시**:

```json
{
    "username": "새사용자",
    "email": "user@example.com",
    "password": "안전한비밀번호",
    "password2": "안전한비밀번호"
}

```

- **응답 예시**:

```json
{
    "id": 1,
    "username": "새사용자",
    "email": "user@example.com"
}

```

### 사용자 프로필

- **URL**: `/api/users/profile/`
- **Method**: `GET`
- **인증**: 필요
- **설명**: 현재 로그인한 사용자의 프로필 정보
- **응답 예시**:

```json
{
    "id": 1,
    "username": "사용자이름",
    "email": "user@example.com",
    "profile": {
        "bio": "자기소개",
        "created_at": "2025-03-04T08:42:49.123456Z"
    }
}

```

## AI 서비스

### 대화 생성

- **URL**: `/api/ai/conversation/`
- **Method**: `POST`
- **인증**: 필요
- **설명**: 새로운 AI 대화 생성
- **요청 예시**:

```json
{
    "message": "안녕하세요, 오늘 날씨는 어때요?"
}

```

- **응답 예시**:

```json
{
    "id": "conv_123456",
    "response": "안녕하세요! 제가 실시간 날씨 정보에 접근할 수는 없지만, 날씨에 관해 도움이 필요하시면 말씀해주세요..",
    "created_at": "2025-03-04T08:42:49.123456Z"
}

```

### 문서 분석

- **URL**: `/api/ai/analyze-document/`
- **Method**: `POST`
- **인증**: 필요
- **설명**: 문서 분석 및 요약
- **요청 예시**:

```json
{
    "document": "분석할 문서 내용..."
}

```

- **응답 예시**:

```json
{
    "summary": "문서 요약 내용...",
    "keywords": ["키워드1", "키워드2", "키워드3"],
    "sentiment": "긍정적"
}

```

## 오류 코드

- `400 Bad Request`: 잘못된 요청 형식
- `401 Unauthorized`: 인증 실패
- `403 Forbidden`: 권한 없음
- `404 Not Found`: 리소스를 찾을 수 없음
- `500 Internal Server Error`: 서버 내부 오류

## API 사용 예시 (Vue.js)

```jsx
// 로그인 요청 예시
async login() {
  try {
    const response = await axios.post('<http://localhost:8000/api/auth/token/>', {
      username: this.username,
      password: this.password
    });

    // 토큰 저장
    localStorage.setItem('access_token', response.data.access);
    localStorage.setItem('refresh_token', response.data.refresh);

    // API 요청에 기본 헤더 설정
    axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access}`;

    // 로그인 성공 후 처리
    this.$router.push('/dashboard');
  } catch (error) {
    console.error('로그인 실패:', error);
    this.errorMessage = '로그인에 실패했습니다. 사용자 이름과 비밀번호를 확인하세요.';
  }
}

```
