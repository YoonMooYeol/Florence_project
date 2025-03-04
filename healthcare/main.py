import os
from openai import OpenAI
from dotenv import load_dotenv
from emotion_analysis.analyzer import EmotionAnalyzer
from conversation.dialogue import DialogueManager
from data_collection.collector import DataCollector
from feedback_generation.generator import FeedbackGenerator
from medical_search.crawler import MedicalCrawler
from utils import format_feedback_for_display, ensure_dir_exists

# 환경 변수 로드
load_dotenv()


def main():
    """메인 함수"""
    print("\n===== 산모 컨디션 체크 시스템 =====\n")
    print(
        "안녕하세요! 오늘 하루 어떻게 지내셨는지 대화를 통해 알아보고 맞춤형 피드백을 제공해 드리겠습니다."
    )
    print("산모 상태에 맞는 의학 정보도 함께 제공됩니다.")
    print("총 10개의 질문을 통해 컨디션을 체크하고 종합적인 피드백을 생성합니다.\n")

    # API 키 확인
    openai_key = os.getenv("OPENAI_API_KEY")
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")

    if not openai_key:
        print("경고: OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        return

    if not firecrawl_key:
        print(
            "경고: FIRECRAWL_API_KEY가 설정되지 않았습니다. 의료 정보 검색 기능이 제한됩니다."
        )

    # OpenAI 클라이언트 초기화
    client = OpenAI()

    # 모듈 초기화
    emotion_analyzer = EmotionAnalyzer(client=client)
    dialogue_manager = DialogueManager()
    data_collector = DataCollector()
    feedback_generator = FeedbackGenerator(client=client)
    medical_crawler = MedicalCrawler(client=client)

    # 새 세션 시작
    data_collector.start_new_session()

    # 대화 진행
    step = 0
    current_emotion = "neutral"  # 초기 감정 상태

    while not dialogue_manager.is_conversation_complete():
        # 다음 질문 가져오기
        question = dialogue_manager.get_next_question(emotion=current_emotion)

        if not question:
            break

        # 질문 표시 및 사용자 응답 받기
        step += 1  # 단계를 먼저 증가시켜 1부터 시작하도록 함
        print(f"\n[{step}/10] {question}")
        answer = input("> ")

        # 이전 대화 내용 가져오기
        previous_interactions = data_collector.get_all_interactions()

        # 맥락을 고려한 감정 분석
        emotion_result = emotion_analyzer.analyze_emotion_with_context(
            question=question, answer=answer, conversation_history=previous_interactions
        )
        current_emotion = emotion_result["emotion"]

        # 분석된 감정 출력 (디버깅용)
        print(
            f"[시스템] 감지된 감정: {current_emotion} (신뢰도: {emotion_result['confidence']:.2f})"
        )

        # 상호작용 기록
        data_collector.record_interaction(
            question=question,
            answer=answer,
            emotion=current_emotion,
            confidence=emotion_result["confidence"],
            step=step - 1,  # 0부터 시작하는 원래 step 값 유지
        )

    print("\n모든 질문이 완료되었습니다. 피드백을 생성 중입니다...\n")

    # 세션 저장
    session_file = data_collector.save_session()

    # 의료 정보 검색
    print("의료 정보를 검색 중입니다...")

    # 모든 상호작용 가져오기
    interactions = data_collector.get_all_interactions()

    # 대화 내용 기반 검색 쿼리 직접 생성 - 하나의 고품질 쿼리로 개선
    search_query = medical_crawler.generate_queries_from_conversation(interactions)[0]

    # 의료 정보 검색 및 처리
    medical_info = {"tips": [], "sources": []}

    search_results = medical_crawler.search_medical_info(
        search_query, limit=1
    )  # 하나의 검색 결과만 가져오기

    if search_results:
        processed_results = medical_crawler.process_search_results(search_results)

        # 팁 및 소스 추가
        medical_info["tips"] = processed_results["tips"]
        medical_info["sources"] = processed_results["sources"]

    # 최대 7개 팁으로 제한
    if len(medical_info["tips"]) > 7:
        medical_info["tips"] = medical_info["tips"][:7]

    # 의료 정보가 없는 경우 기본 메시지 추가
    if not medical_info["tips"]:
        medical_info["tips"] = [
            "관련 의료 정보를 찾을 수 없습니다. 궁금한 점이 있으시면 의료 전문가와 상담하세요."
        ]

    # 피드백 생성
    feedback = feedback_generator.generate_feedback(interactions, medical_info)

    # 피드백 저장
    session_id = data_collector.get_session_data()["session_id"]
    feedback_file = feedback_generator.save_feedback(feedback, session_id)

    # 피드백 표시
    formatted_feedback = format_feedback_for_display(feedback)
    print(formatted_feedback)

    print(f"\n피드백이 '{feedback_file}' 파일에 저장되었습니다.")
    print("\n===== 산모 컨디션 체크 완료 =====\n")


if __name__ == "__main__":
    # 출력 디렉토리 확인
    ensure_dir_exists("output")
    main()
