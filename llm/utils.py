import logging
import os
from dotenv import load_dotenv
from openai import OpenAI

# RAG 서비스 임포트
from .rag_service import rag_service

# .env 파일 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)

def get_system_prompt():
    """시스템 프롬프트 생성"""
    return "You are an expert providing medically accurate information about pregnancy and childbirth. Always respond in a friendly and clear manner. Respond in the same language as the user's query."

def process_llm_query(user_id, query_text, user_info=None):
    """
    LLM에 질문을 처리하는 함수
    
    Args:
        user_id: 사용자 ID
        query_text: 질문 내용
        user_info: 사용자 정보 (선택)
        
    Returns:
        dict: LLM 응답
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OpenAI API 키가 설정되지 않았습니다.")
        return {"response": "서비스 구성 오류가 발생했습니다. 관리자에게 문의하세요."}
    
    # RAG 서비스 사용 설정
    use_rag = os.getenv('USE_RAG', 'true').lower() == 'true'
    
    # RAG 서비스를 통한 응답 시도
    if use_rag:
        try:
            rag_response = rag_service.query(query_text, user_info)
            
            # RAG 응답이 성공적으로 생성된 경우
            if rag_response['using_rag']:
                logger.info("RAG를 사용하여 질의응답을 처리했습니다.")
                return {
                    "response": rag_response['response'],
                    "source_documents": rag_response['source_documents'],
                    "using_rag": True
                }
            else:
                logger.warning("RAG 서비스를 사용할 수 없어 일반 LLM으로 대체합니다.")
        except Exception as e:
            logger.error(f"RAG 질의응답 중 오류 발생: {str(e)}")
            logger.exception("상세 오류 내용:")
    
    # RAG 서비스를 사용할 수 없거나 실패한 경우 기존 OpenAI API 사용
    model = os.getenv('LLM_MODEL', 'gpt-4')
    
    # 사용자 컨텍스트 생성
    user_context = ""
    if user_info:
        if user_info.get('name'):
            user_context += f"사용자 이름: {user_info['name']}\n"
        if user_info.get('is_pregnant'):
            user_context += "사용자는 임신 중입니다.\n"
        if user_info.get('pregnancy_week'):
            user_context += f"임신 {user_info['pregnancy_week']}주차입니다.\n"
    
    # 프롬프트 생성
    system_prompt = get_system_prompt()
    
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{user_context}\n\n{query_text}"}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        response_text = response.choices[0].message.content.strip()
        return {
            "response": response_text,
            "source_documents": [],
            "using_rag": False
        }
    
    except Exception as e:
        logger.error(f"LLM API 호출 중 오류 발생: {str(e)}")
        return {"response": "죄송합니다. 요청을 처리하는 중에 오류가 발생했습니다. 잠시 후 다시 시도해주세요."} 