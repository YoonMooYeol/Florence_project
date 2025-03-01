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
LLM_API_KEY=your_openai_api_key
LLM_API_URL=https://api.openai.com/v1/chat/completions
```

5. 데이터베이스 마이그레이션

```bash
python manage.py migrate
```

6. 서버 실행

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