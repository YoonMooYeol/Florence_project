import logging
import os
from dotenv import load_dotenv
from openai import OpenAI

from accounts.models import Pregnancy  # Pregnancy 모델 임포트

# .env 파일 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


# def process_llm_query(user_id, query_text, user_info=None, chat_history=None):
#     """
#     LLM에 질문을 처리하는 함수
    
#     Args:
#         user_id: 사용자 ID
#         query_text: 질문 내용
#         user_info: 사용자 정보 (선택)
#         chat_history: 이전 대화 기록 (선택)
        
#     Returns:
#         dict: LLM 응답
#     """
#     api_key = os.getenv('OPENAI_API_KEY')
#     if not api_key:
#         logger.error("OpenAI API 키가 설정되지 않았습니다.")
#         return {"response": "서비스 구성 오류가 발생했습니다. 관리자에게 문의하세요."}
    
#     # 대화 기록이 없으면 빈 리스트로 초기화
#     if chat_history is None:
#         chat_history = []
    
#     # RAG 서비스 사용 설정
#     use_rag = os.getenv('USE_RAG', 'true').lower() == 'true'
    
#     # RAG 서비스를 통한 응답 시도
#     if use_rag:
#         try:
#             # user_info를 user_context로 사용
#             rag_response = rag_service.query(query_text, user_info)
            
#             # RAG 응답이 성공적으로 생성된 경우
#             if rag_response['using_rag']:
#                 logger.info("RAG를 사용하여 질의응답을 처리했습니다.")
#                 return {
#                     "response": rag_response['response'],
#                     "source_documents": rag_response['source_documents'],
#                     "using_rag": True
#                 }
#             else:
#                 logger.warning("RAG 서비스를 사용할 수 없어 일반 LLM으로 대체합니다.")
#         except Exception as e:
#             logger.error(f"RAG 질의응답 중 오류 발생: {str(e)}")
#             logger.exception("상세 오류 내용:")
    
#     # RAG 서비스를 사용할 수 없거나 실패한 경우 기존 OpenAI API 사용
#     model = os.getenv('LLM_MODEL', 'gpt-4o')
    
#     # 사용자 컨텍스트 생성
#     user_context = ""
#     if user_info:
#         if user_info.get('name'):
#             user_context += f"사용자 이름: {user_info['name']}\n"
#         if user_info.get('is_pregnant'):
#             user_context += "사용자는 임신 중입니다.\n"
#         try:
#             pregnancy_info = Pregnancy.objects.filter(user_id=user_id).first()  # 사용자 ID로 임신 정보 조회
#             print(pregnancy_info)
#             if pregnancy_info:
#                 if pregnancy_info.current_week:
#                     user_context += f"임신 {pregnancy_info.current_week}주차입니다.\n"
#         except Pregnancy.DoesNotExist:
#             logger.warning("사용자의 임신 정보를 찾을 수 없습니다.")
    
#     # 프롬프트 생성
#     system_prompt = get_system_prompt()
    
#     try:
#         client = OpenAI(api_key=api_key)
        
#         # 메시지 리스트 생성
#         messages = [
#             {"role": "system", "content": system_prompt}
#         ]
        
#         # 이전 대화 기록 추가 (최대 10개)
#         if chat_history:
#             # 리스트 길이가 너무 길면 자르기 (토큰 제한 고려)
#             for message in chat_history[-10:]:
#                 messages.append(message)
        
#         # 현재 질문 추가
#         messages.append({"role": "user", "content": f"{user_context}\n\n{query_text}"})
        
#         response = client.chat.completions.create(
#             model=model,
#             messages=messages,
#             temperature=0.3,
#             max_tokens=2000
#         )
        
#         response_text = response.choices[0].message.content.strip()
#         return {
#             "response": response_text,
#             "source_documents": [],
#             "using_rag": False
#         }
    
#     except Exception as e:
#         logger.error(f"LLM API 호출 중 오류 발생: {str(e)}")
#         return {"response": "죄송합니다. 요청을 처리하는 중에 오류가 발생했습니다. 잠시 후 다시 시도해주세요."} 