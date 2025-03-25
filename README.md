# 👶🏻 Florence Project _ 누리달

<br>

![누리달](static/florence.png "누리달")

[➡️ 누리달 홈페이지 바로가기](https://www.nooridal.com/)



# 💡목차

---

### 1️⃣ [프로젝트 소개](#프로젝트-소개)
### 2️⃣ [기술 스택](#기술-스택)
### 3️⃣ [설치 및 설정](#설치-및-설정)
### 4️⃣ [실행 방법](#실행-방법)
### 5️⃣ [프로젝트 구조](#프로젝트-구조)
### 6️⃣ [API 가이드](#api-가이드)

<br>

## 💁🏻‍♀️ 프로젝트 소개

---

## 🌙 누리달: AI 기반 산전 관리 시스템


## 프로젝트 개요

>대한민국의 일부 지역, 특히 **서울 이외의 소도시에서는 산부인과 의료 접근성이 낮아** 임산부들이 적절한 산전 및 산후 관리를 받기 어려운 현실입니다.  
또한, **미성년 임산부들은 사회적 편견과 경제적 어려움**으로 인해 필요한 의료 지원과 상담을 충분히 받지 못하고 있습니다.

>누리달은 이러한 문제를 해결하고자 **AI 기반 산전 관리 시스템**을 개발하여,  
**의료 정보 제공, 맞춤 건강 관리, 정부 지원 정책 안내**를 통해 **임산부와 신생아의 건강을 증진**하는 것을 목표로 합니다.    



## 주요 목표

>1. **의료 접근성 향상**
> - AI 에이전트를 활용한 **철저하게 검증된 맞춤형 의료 정보 제공**
> - 신뢰할 수 있는 건강 관리 정보로 **임산부의 모성 건강 증진**

>2.  **정부 지원 정책 제공**
>
>- **임산부를 위한 지원 정책**을 쉽고 간편하게 검색
>   - 거주 지역 기반으로 **맞춤형 정책 정보 추천**

>3. **개인 맞춤 건강 관리**
>- **AI 분석을 통한 임산부 개개인의 건강 상태 관리**
>- 정기적인 건강 체크 및 **맞춤형 케어 솔루션 제공**



## 기대 효과

>"누리달은 단순한 AI 기반 시스템이 아닌,  
**대한민국에서 태어나는 소중한 생명을 지키는 데 기여하는 서비스**가 되고자 합니다."


>- **의료 정보 접근성 개선**으로 임산부의 건강 증진
>- **정부 지원 정보 제공**을 통한 실질적 지원 확대
>- **AI 맞춤 케어**로 모성 사망률 감소에 기여

<br>

## 🔗 기술 스택

---
- 웹 서버: Django + Gunicorn + Nginx
- 비동기 작업: Celery + Celery Beat
- 메시지 브로커: Redis
- 데이터베이스: PostgreSQL
- 배포: Docker, Docker Compose, AWS Elastic Beanstalk


## ⚙️ 로컬 개발 환경 설정

---

### 사전 요구사항

- Docker 및 Docker Compose
- Python 3.12 이상 설치

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

## 📬 AWS Elastic Beanstalk 배포 방법

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

2. 환경 생성

```bash
eb create florence-env --single --instance-type t2.small
```

3. 배포

```bash
eb deploy
```

4. 환경 변수 설정

```bash
eb setenv SECRET_KEY=your-secret-key DB_NAME=florence_db DB_USER=florence_user DB_PASSWORD=your-password
```

5. 데이터베이스 마이그레이션

```bash
python manage.py migrate
```

### 백엔드 실행

```bash
python manage.py runserver 0.0.0.0:8000
```
<br>

##  🔧 유지보수

---

### 데이터베이스 백업

AWS RDS를 사용할 경우 자동 백업 설정을 권장합니다.

### 로그 확인

```bash
eb logs
```

### 모니터링

AWS CloudWatch를 통해 시스템 모니터링을 설정할 수 있습니다.

---
## 📂 프로젝트 구조

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

## 🫧 문제 해결

---
### 일반적인 문제

1. 데이터베이스 연결 오류 - 보안 그룹 및 네트워크 설정 확인
2. 정적 파일 접근 불가 - collectstatic 명령 실행 및 S3 버킷 권한 확인

### 지원 및 문의

문제가 발생할 경우 프로젝트 관리자에게 문의하세요.

<br>

# 📚 API 가이드

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

```javascript
// 로그인 요청 예시
async login() {
  try {
    const response = await axios.post('http://localhost:8000/api/auth/token/', {
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
