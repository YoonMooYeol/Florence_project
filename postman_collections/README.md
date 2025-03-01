# Florence LLM API 포스트맨 컬렉션

이 디렉토리에는 Florence 프로젝트의 LLM API를 테스트하기 위한 포스트맨 컬렉션과 환경 설정 파일이 포함되어 있습니다.

## 파일 설명

- `florence_llm_api.json`: LLM API 포스트맨 컬렉션 파일
- `florence_llm_environment.json`: 포스트맨 환경 설정 파일

## 포스트맨에서 임포트하는 방법

1. 포스트맨을 실행합니다.
2. 왼쪽 상단의 `Import` 버튼을 클릭합니다.
3. `Upload Files` 탭을 선택하고 `florence_llm_api.json` 파일을 선택합니다.
4. 같은 방법으로 `florence_llm_environment.json` 파일도 임포트합니다.
5. 오른쪽 상단의 환경 선택 드롭다운에서 `Florence LLM Environment`를 선택합니다.
6. 환경 설정 값을 실제 서버 정보와 사용자 정보로 업데이트합니다.

## 환경 변수 설정

포스트맨 환경 설정에서 다음 변수들을 업데이트해야 합니다:

- `base_url`: API 서버 URL (예: http://localhost:8000 또는 실제 서버 URL)
- `user_id`: 테스트에 사용할 사용자 UUID
- `auth_token`: 인증 토큰 (Bearer 토큰)
- `conversation_id`: 테스트에 사용할 대화 ID (UUID 형식)

## 질문 API 입력 문제 해결 방법

LLM 질문 API 요청이 제대로 작동하지 않는 경우 다음 사항을 확인하세요:

1. **인증 토큰 확인**:
   - 환경 변수에서 `auth_token` 값을 실제 발급받은 유효한 토큰으로 변경했는지 확인하세요.
   - 기본값인 `your_auth_token_here`는 실제 토큰이 아닙니다.
   - 토큰은 다음과 같이 발급받을 수 있습니다:
     ```
     POST /v1/accounts/login/
     {
       "email": "your_email@example.com",
       "password": "your_password"
     }
     ```

2. **사용자 ID 확인**:
   - 환경 변수에서 `user_id` 값을 실제 존재하는 사용자 ID로 변경했는지 확인하세요.
   - 기본값인 `9fa5edd1-d4be-44bb-a2c7-d3da4f8717bd`는 예시 ID입니다.

3. **서버 연결 확인**:
   - API 서버가 실행 중인지 확인하세요.
   - 환경 변수에서 `base_url` 값이 올바른지 확인하세요.
   - 로컬 개발 환경에서는 `http://localhost:8000`이 기본값입니다.

4. **요청 형식 확인**:
   - 요청 본문(Body)의 JSON 형식이 올바른지 확인하세요.
   - 필수 필드인 `user_id`와 `query_text`가 포함되어 있는지 확인하세요.

5. **응답 확인**:
   - 오류 응답이 있는 경우 응답 본문에서 오류 메시지를 확인하세요.
   - 일반적인 오류 코드:
     - 400: 잘못된 요청 형식
     - 401: 인증 실패
     - 404: 리소스를 찾을 수 없음
     - 500: 서버 내부 오류

6. **CORS 문제**:
   - 브라우저에서 API를 직접 호출하는 경우 CORS 설정을 확인하세요.
   - 포스트맨에서는 CORS 제한이 적용되지 않습니다.

## API 엔드포인트

### LLM 질문 API

- **엔드포인트**: `POST /v1/llm/`
- **설명**: 산모 건강 관련 질문을 LLM에 전송하고 응답을 받는 API
- **요청 예시**:
  ```json
  {
    "user_id": "9fa5edd1-d4be-44bb-a2c7-d3da4f8717bd",
    "query_text": "임신 중 건강한 식단은 어떻게 구성해야 하나요?",
    "preferences": {
      "response_style": "detailed",
      "include_references": true
    },
    "pregnancy_week": 20
  }
  ```
- **응답 예시**:
  ```json
  {
    "response": "임신 중 건강한 식단은 다양한 영양소를 균형 있게 섭취하는 것이 중요합니다...",
    "follow_up_questions": [
      "임신 중 피해야 할 음식은 무엇인가요?",
      "임신 중 필요한 영양제는 어떤 것이 있나요?"
    ],
    "query_info": {
      "query_type": "nutrition",
      "keywords": ["임신", "식단", "영양"]
    }
  }
  ```

### 대화 조회 API

- **엔드포인트**: `GET /v1/llm/conversations`
- **설명**: 사용자의 LLM 대화 기록을 조회하는 API
- **쿼리 파라미터**:
  - `user_id`: 사용자 UUID (필수)
  - `query_type`: 질문 유형으로 필터링 (선택)

### 대화 수정 API

- **엔드포인트**: `PUT /v1/llm/conversations/edit`
- **설명**: 사용자의 LLM 대화를 수정하는 API
- **쿼리 파라미터**:
  - `user_id`: 사용자 UUID (필수)
  - `conversation_id`: 대화 ID (UUID 형식) (필수)
- **요청 예시**:
  ```json
  {
    "query": "수정된 질문 내용입니다."
  }
  ```

### 대화 삭제 API

- **엔드포인트**: `DELETE /v1/llm/conversations/delete`
- **설명**: 사용자의 LLM 대화를 삭제하는 API
- **쿼리 파라미터**:
  - `user_id`: 사용자 UUID (필수)
  - `conversation_id`: 대화 ID (UUID 형식) (선택, 없으면 모든 대화 삭제)
- **요청 예시**:
  ```json
  {
    "delete_mode": "all"
  }
  ```
  - `delete_mode`: 삭제 모드 (`all`: 모두 삭제, `query_only`: 질문만 삭제)

## 주의사항

- API 호출 시 인증 토큰이 필요합니다. 환경 변수의 `auth_token` 값을 실제 토큰으로 업데이트하세요.
- 실제 서버 URL과 사용자 정보를 환경 변수에 설정해야 합니다.
- LLM 질문 API에는 5가지 예제 질문이 포함되어 있습니다. 필요에 따라 질문 내용과 파라미터를 수정하여 사용하세요.