import logging
import time
import json
import threading
from functools import lru_cache
from django.conf import settings
import openai

# 로깅 설정
logger = logging.getLogger(__name__)

# OpenAI API 키 설정
openai.api_key = getattr(settings, 'OPENAI_API_KEY', None)

# 시스템 프롬프트 캐싱
@lru_cache(maxsize=1)
def get_system_prompt():
    """시스템 프롬프트 생성 - LRU 캐시 사용으로 반복 호출 시 성능 향상"""
    return "You are an expert providing medically accurate information about pregnancy and childbirth. Always respond in a friendly and clear manner. Respond in the same language as the user's query."

class PyLLMService:
    """
    단일 프롬프트 기반 LLM 서비스
    
    이 클래스는 OpenAI API를 사용하여 LLM과 통신하며, 단일 프롬프트로 
    사용자 질문에 대한 응답을 생성합니다. 복잡한 분기 처리나 여러 프롬프트 없이
    최적의 속도로 응답을 생성합니다.
    
    Attributes:
        api_key (str): OpenAI API 키
        model (str): 사용할 LLM 모델 (기본값: gpt-4)
    """
    
    # 클래스 변수로 클라이언트 인스턴스 공유
    _client_instance = None
    _client_lock = threading.Lock()
    
    def __init__(self, api_key=None):
        """
        PyLLMService 초기화
        
        Args:
            api_key (str, optional): OpenAI API 키 (없으면 settings에서 가져옴)
        """
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        if not self.api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
            
        self.model = getattr(settings, 'LLM_MODEL', 'gpt-4')
        
        # OpenAI API 키 설정
        openai.api_key = self.api_key
        
        # OpenAI 클라이언트 초기화 (싱글톤 패턴)
        self._get_client()
    
    def _get_client(self):
        """OpenAI 클라이언트 인스턴스 반환 (싱글톤 패턴)"""
        if PyLLMService._client_instance is None:
            with PyLLMService._client_lock:
                if PyLLMService._client_instance is None:
                    PyLLMService._client_instance = openai.OpenAI(api_key=self.api_key)
        return PyLLMService._client_instance
    
    def process_query(self, user_id, query_text, user_info=None):
        """
        사용자 질문 처리 및 응답 생성 (단일 프롬프트 사용)
        
        Args:
            user_id (str): 사용자 UUID
            query_text (str): 사용자 질문 내용
            user_info (dict, optional): 사용자 정보 (이름, 임신 여부, 임신 주차 등)
            
        Returns:
            dict: 응답 결과 딕셔너리
                {
                    "response": "LLM 응답 내용"
                }
        """
        # 사용자 정보 문자열 생성 - 최적화
        user_context = self._generate_user_context(user_info)
        
        # 단일 프롬프트 생성 - 문자열 연결 최적화
        prompt = self._generate_prompt(query_text, user_context)
        
        try:
            # LLM 호출
            start_time = time.time()
            response_text = self._call_llm(prompt)
            logger.info(f"LLM 응답 시간: {time.time() - start_time:.2f}초")
            
            # JSON 응답 파싱
            result = self._parse_json_response(response_text)
            
            return result
            
        except Exception as e:
            logger.error(f"LLM 응답 생성 오류: {str(e)}")
            raise
    
    def _generate_user_context(self, user_info):
        """사용자 정보 문자열 생성 - 최적화"""
        if not user_info or not isinstance(user_info, dict):
            return ""
            
        context_parts = []
        
        if user_info.get("is_pregnant"):
            context_parts.append("사용자는 현재 임신 중이며")
            if "pregnancy_week" in user_info:
                context_parts.append(f"임신 {user_info['pregnancy_week']}주차입니다")
        
        if user_info.get("gender"):
            context_parts.append(f"사용자의 성별은 {user_info['gender']}입니다")
        
        if not context_parts:
            return ""
            
        return ". ".join(context_parts) + "."
    
    @lru_cache(maxsize=10)
    def _generate_prompt(self, query_text, user_context):
        """최적화된 프롬프트 생성"""
        return f"""
# 임신/출산 관련 질문에 대한 응답

## 사용자 정보
{user_context if user_context else "사용자 정보가 제공되지 않았습니다."}

## 사용자 질문
{query_text}

## 응답 요구사항
1. 사용자 질문에 대해 정확하고 의학적으로 검증된 정보를 제공해주세요.
2. 응답은 친절하고 이해하기 쉬운 말투로 작성해주세요.
3. 심각한 의학적 증상에 대해서는 반드시 의사와 상담할 것을 권고해주세요.
4. 불확실한 정보는 제공하지 말고, 확신할 수 있는 정보만 제공해주세요.
5. 사용자 질문의 언어와 동일한 언어로 응답해주세요.

## 응답 형식
JSON 형식으로 다음 정보를 포함하여 응답해주세요:
```json
{{
    "response": "사용자 질문에 대한 상세한 응답"
}}
```

JSON 형식으로만 응답해주세요. 다른 텍스트는 포함하지 마세요.
"""
    
    def _call_llm(self, prompt, temperature=0.3, max_tokens=2000):
        """
        LLM API 호출 - 재사용 가능한 클라이언트 활용
        
        Args:
            prompt (str): LLM에게 전달할 프롬프트
            temperature (float, optional): 응답의 창의성 정도 (0.0~1.0)
            max_tokens (int, optional): 응답의 최대 토큰 수
            
        Returns:
            str: LLM 응답 텍스트
            
        Raises:
            Exception: API 호출 중 오류 발생 시
        """
        logger.info(f"LLM API 호출: {prompt[:50]}...")
        
        # 클라이언트 가져오기
        client = self._get_client()
        
        # OpenAI API 호출 - 재사용 가능한 클라이언트 사용
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    
    def _parse_json_response(self, response_text):
        """
        LLM 응답에서 JSON 추출 및 파싱 - 최적화
        
        Args:
            response_text (str): LLM 응답 텍스트
            
        Returns:
            dict: 파싱된 JSON 응답
            
        Raises:
            Exception: JSON 파싱 오류 시
        """
        try:
            # JSON 부분 추출 - 최적화된 방식
            json_str = response_text
            
            # 코드 블록 마커 제거
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.rfind("```")
                if end > start:
                    json_str = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.rfind("```")
                if end > start:
                    json_str = response_text[start:end].strip()
            
            # JSON 파싱
            result = json.loads(json_str)
            
            # 필수 필드 확인 및 추가
            if "response" not in result:
                result["response"] = "응답을 생성하는 중 오류가 발생했습니다."
            
            # follow_up_questions 필드가 있으면 제거
            if "follow_up_questions" in result:
                del result["follow_up_questions"]
            
            return result
            
        except Exception as e:
            logger.error(f"JSON 파싱 오류: {str(e)}")
            raise 