# Florence 프로젝트

## 목차
- [프로젝트 소개](#프로젝트-소개)
- [기술 스택](#기술-스택)
- [설치 및 설정](#설치-및-설정)
- [실행 방법](#실행-방법)
- [프로젝트 구조](#프로젝트-구조)
- [API 가이드](#api-가이드)

## 프로젝트 소개
Florence 프로젝트는 Django 백엔드와 Vue.js 3 프론트엔드를 사용하는 웹 애플리케이션입니다. 이 프로젝트는 LangChain과 OpenAI를 활용한 AI 기능을 포함하고 있습니다.

## 기술 스택
### 백엔드
- Django 4.2
- Django REST Framework 3.15.2
- JWT 인증 (djangorestframework-simplejwt)
- PostgreSQL
- LangChain 및 OpenAI 통합
- ChromaDB (벡터 데이터베이스)

## 설치 및 설정

### 사전 요구사항
- Python 3.11 이상
- PostgreSQL

### 백엔드 설정
1. 저장소 클론
```bash
git clone https://github.com/yourusername/Florence_project.git
cd Florence_project
```

2. 가상 환경 생성 및 활성화
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

3. 의존성 설치
```bash
pip install -r requirements.txt
```

4. 환경 변수 설정 (.env 파일 생성)
```
DEBUG=True
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:password@localhost:5432/florence_db
OPENAI_API_KEY=your_openai_api_key
```

5. 데이터베이스 마이그레이션
```bash
python manage.py migrate
```

### 백엔드 실행
```bash
python manage.py runserver 0.0.0.0:8000
```

## 프로젝트 구조
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
    "response": "안녕하세요! 제가 실시간 날씨 정보에 접근할 수는 없지만, 날씨에 관해 도움이 필요하시면 말씀해주세요.",
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