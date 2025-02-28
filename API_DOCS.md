# Florence 프로젝트 API 기능 정리

## RAG API 엔드포인트

### 1. 자동 임베딩 API (`/v1/rag/auto-embed/`)

**설명**: 다양한 파일 형식(CSV, JSON, RDF, XML)을 자동으로 감지하고 임베딩하는 통합 API

**요청 방법**: POST

**파라미터**:
- `data_dir`: (선택) 데이터 디렉토리 경로. 기본값은 "data"
- `file_types`: (선택) 처리할 파일 유형 목록. 기본값은 ["csv", "json", "rdf", "xml"]
- `force_reprocess`: (선택) 이미 처리된 파일도 다시 처리할지 여부. 기본값은 false

**응답 예시**:
```json
{
  "message": "자동 임베딩 완료",
  "total_files_found": 3,
  "new_files_processed": 3,
  "skipped_files": 0,
  "failed_files": 0,
  "total_documents_embedded": 7,
  "processing_time_seconds": 2.94,
  "file_details": [
    {
      "file_path": "data/csv/test_emotions.csv",
      "file_type": "csv",
      "status": "success",
      "documents_embedded": 4
    },
    {
      "file_path": "data/json/test_conversation.json",
      "file_type": "json",
      "status": "success",
      "documents_embedded": 3
    },
    {
      "file_path": "data/rdf/wellness.rdf",
      "file_type": "rdf",
      "status": "success",
      "documents_embedded": 0
    }
  ]
}
```

### 2. RAG 쿼리 API (`/v1/rag/query/`)

**설명**: 임베딩된 데이터를 기반으로 질의응답을 수행하는 API

**요청 방법**: POST

**파라미터**:
- `query`: (필수) 쿼리 텍스트

**응답 예시**:
```json
{
  "message": "RAG 쿼리 완료",
  "query": "오늘 기분이 좋지 않아",
  "result": "오늘 기분이 좋지 않으신가요? | 오늘 마음이 편치 않으신 것 같네요. | 기분이 좋지 않으신 하루를 보내고 계신가요?"
}
```

## 변경 사항 요약

1. **API 정리**
   - 불필요한 API를 제거하고 핵심 기능만 유지
   - 자동 임베딩 API와 기본 쿼리 API만 남김

2. **코드 중복 제거**
   - 중복된 파일 처리 로직을 통합하여 코드 유지보수성 향상
   - 일관된 에러 처리 및 응답 형식 제공

3. **사용자 경험 개선**
   - 진행 상황 시각화 기능 추가
   - 이미 처리된 파일 자동 감지 및 스킵 기능
   - 상세한 처리 결과 제공

4. **성능 최적화**
   - 비동기 임베딩 생성 기능 구현
   - 배치 처리를 통한 대용량 데이터 처리 효율성 향상

# Florence 프로젝트 API 정리 완료

## 테스트 결과

- 핵심 API가 정상적으로 작동합니다.
- 자동 임베딩 API가 다양한 파일 형식을 처리할 수 있습니다.
- 이미 처리된 파일은 자동으로 건너뛰어 중복 처리를 방지합니다.

## 다음 단계

1. 프론트엔드에서 새로운 API 구조에 맞게 호출 코드 업데이트
2. 대용량 데이터셋에 대한 성능 테스트 진행
3. 사용자 매뉴얼 업데이트
API 정리 완료 요약
