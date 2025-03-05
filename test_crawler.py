from healthcare.medical_search.crawler import MedicalCrawler
from openai import OpenAI
import os

# 환경 변수에서 프로젝트 루트 경로 추가
os.environ['PYTHONPATH'] = os.environ.get('PYTHONPATH', '') + ':' + os.getcwd()

# OpenAI 클라이언트 초기화
client = OpenAI()

# 크롤러 초기화
crawler = MedicalCrawler(client=client)

# 테스트 쿼리
test_query = "임신 중 건강한 식단과 운동 방법"

print(f"테스트 쿼리: {test_query}")

# 의료 정보 검색
search_results = crawler.search_medical_info(test_query, limit=3)

# 검색 결과 처리
if search_results:
    print(f"검색 결과: {len(search_results)}개의 URL")
    
    # 첫 번째 결과 확인
    if len(search_results) > 0:
        first_result = search_results[0]
        print(f"첫 번째 결과 제목: {first_result.get('title', '제목 없음')}")
        content = first_result.get('content', '')
        print(f"내용 미리보기: {content[:200]}...")
else:
    print("검색 결과가 없습니다.")

# 의료 정보 처리
processed_info = crawler.process_search_results(search_results)

# 팁 출력
print("\n=== 처리된 의료 정보 ===")
for i, tip in enumerate(processed_info.get("tips", []), 1):
    print(f"{i}. {tip}")

# 소스 출력
print("\n=== 소스 ===")
for source in processed_info.get("sources", []):
    print(f"- {source}") 