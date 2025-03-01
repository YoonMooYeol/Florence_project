# Florence 프로젝트 LLM API 사용 가이드

Florence 프로젝트는 임산부를 위한 건강 정보 제공 서비스입니다. 이 문서는 Florence 프로젝트의 LLM(Large Language Model) API 사용 방법을 설명합니다.

## 목차

1. [API 개요](#api-개요)
2. [API 엔드포인트](#api-엔드포인트)
3. [인증 방법](#인증-방법)
4. [요청 및 응답 형식](#요청-및-응답-형식)
5. [질문 유형](#질문-유형)
6. [사용 예시](#사용-예시)
7. [오류 처리](#오류-처리)
8. [제한 사항](#제한-사항)

## API 개요

Florence LLM API는 임신 관련 질문에 대한 정확하고 신뢰할 수 있는 정보를 제공합니다. 이 API는 다음과 같은 기능을 제공합니다:

- 임신 주차별 정보 제공
- 임신 중 증상에 대한 정보 제공
- 임신 중 식이 관련 정보 제공
- 임신 중 검사 관련 정보 제공
- 임신 관련 복지 정보 제공
- 일반적인 임신 관련 질문에 대한 답변

## API 엔드포인트

### 기본 URL

```
http://localhost:8000/v1/
```

### LLM API 엔드포인트

```
POST /v1/sanitization/api/llm/
```

### 임신 주차 정보 API 엔드포인트

```
GET /v1/sanitization/api/week/{week}/
```

### 사용자 상호작용 조회 API 엔드포인트

```
GET /v1/sanitization/api/interactions/?user_id={user_id}
```

## 인증 방법

현재 버전에서는 별도의 인증 과정 없이 API를 사용할 수 있습니다. 하지만 사용자 식별을 위해 유효한 UUID 형식의 `user_id`가 필요합니다.

## 요청 및 응답 형식

### LLM API 요청 형식

```json
{
  "user_id": "8d58b7eb-a37e-4880-ac0e-32b766ffbcfa",  // UUID 형식의 사용자 ID (필수)
  "query_text": "임신 10주차에는 어떤 변화가 있나요?",  // 질문 내용 (필수)
  "pregnancy_week": 10,  // 임신 주차 (선택)
  "preferences": {  // 사용자 설정 (선택)
    "language": "ko",
    "detail_level": "high"
  }
}
```

### LLM API 응답 형식

```json
{
  "response": "안녕하세요! 요청하신 임신 정보에 대해 알려드립니다...",  // LLM 응답
  "follow_up_questions": [  // 후속 질문 제안
    "임신 10주에 꼭 받아야 하는 검사는 무엇인가요?",
    "임신 10주에 좋은 영양제는 무엇인가요?"
  ],
  "query_info": {  // 질문 분석 정보
    "query_type": "pregnancy_week",
    "keywords": {
      "week": 10
    },
    "original_query": "임신 10주차에는 어떤 변화가 있나요?"
  }
}
```

### 임신 주차 정보 API 응답 형식

```json
{
  "week": 20,
  "label": "임신 20주차",
  "data": {
    "summary": { ... },
    "relations": { ... },
    "resource_uri": "http://www.wellness.ai/resource/...",
    "week": 20
  }
}
```

## 질문 유형

Florence LLM API는 다음과 같은 질문 유형을 지원합니다:

1. **pregnancy_week**: 임신 주차별 정보 관련 질문
   - 예: "임신 10주차에는 어떤 변화가 있나요?"
   - 키워드: 주차, 개월, 주, 개월차, 몇 주, 몇 개월

2. **symptom**: 임신 중 증상 관련 질문
   - 예: "임신 중 입덧이 심할 때 어떻게 해야 하나요?"
   - 키워드: 아파요, 통증, 불편, 증상, 느껴요, 저려요, 붓고, 메스꺼움, 구토, 불면, 입덧

3. **food**: 임신 중 식이 관련 질문
   - 예: "임신 중에 커피를 마셔도 되나요?"
   - 키워드: 먹어도, 음식, 식품, 식이, 섭취, 음료, 마셔도, 식단, 영양

4. **examination**: 임신 중 검사 관련 질문
   - 예: "임신 20주차에는 어떤 검사를 받아야 하나요?"
   - 키워드: 검사, 진단, 촬영, 초음파, 소변검사

5. **welfare**: 임신 관련 복지 정보 질문
   - 예: "임신 중에 받을 수 있는 정부 지원은 무엇이 있나요?"
   - 키워드: 지원, 혜택, 카드, 보험, 복지

6. **general**: 일반적인 임신 관련 질문
   - 예: "임신 중에 운동은 어떻게 해야 하나요?"

## 사용 예시

### cURL을 사용한 LLM API 호출 예시

```bash
curl -X POST http://localhost:8000/v1/sanitization/api/llm/ \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "8d58b7eb-a37e-4880-ac0e-32b766ffbcfa",
    "query_text": "임신 10주차에는 어떤 변화가 있나요?"
  }'
```

### Python을 사용한 LLM API 호출 예시

```python
import requests
import json
import uuid

# API 엔드포인트
url = "http://localhost:8000/v1/sanitization/api/llm/"

# 요청 데이터
data = {
    "user_id": str(uuid.uuid4()),  # 새로운 UUID 생성
    "query_text": "임신 10주차에는 어떤 변화가 있나요?"
}

# API 호출
response = requests.post(url, json=data)

# 응답 처리
if response.status_code == 200:
    result = response.json()
    print("응답:", result["response"])
    print("\n후속 질문:")
    for question in result["follow_up_questions"]:
        print(f"- {question}")
else:
    print(f"오류: {response.status_code}")
    print(response.text)
```

### JavaScript를 사용한 LLM API 호출 예시

```javascript
// API 엔드포인트
const url = 'http://localhost:8000/v1/sanitization/api/llm/';

// 요청 데이터
const data = {
  user_id: '8d58b7eb-a37e-4880-ac0e-32b766ffbcfa',
  query_text: '임신 10주차에는 어떤 변화가 있나요?'
};

// API 호출
fetch(url, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
})
.then(response => response.json())
.then(result => {
  console.log('응답:', result.response);
  console.log('\n후속 질문:');
  result.follow_up_questions.forEach(question => {
    console.log(`- ${question}`);
  });
})
.catch(error => {
  console.error('오류:', error);
});
```

## 오류 처리

API는 다음과 같은 HTTP 상태 코드를 반환할 수 있습니다:

- **200 OK**: 요청이 성공적으로 처리됨
- **400 Bad Request**: 잘못된 요청 형식
- **404 Not Found**: 요청한 리소스를 찾을 수 없음
- **500 Internal Server Error**: 서버 내부 오류

오류 응답 예시:

```json
{
  "error": "잘못된 요청 형식",
  "details": {
    "user_id": ["이 필드는 필수 항목입니다."]
  }
}
```

## 제한 사항

1. 현재 버전에서는 한국어 질문만 지원합니다.
2. 사용자 ID는 반드시 유효한 UUID 형식이어야 합니다.
3. 임신 주차 정보는 일부 주차에 대해서만 제공됩니다.
4. API 응답 시간은 서버 부하에 따라 달라질 수 있습니다.
5. 의학적 응급 상황에서는 이 API를 사용하지 말고 즉시 의료 전문가에게 상담하세요.

---

© 2025 Florence Project Team. All rights reserved. 