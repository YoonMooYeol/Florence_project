import re
import logging
import time
import json
from django.conf import settings
import openai

# 로깅 설정
logger = logging.getLogger(__name__)

# OpenAI API 키 설정
openai.api_key = getattr(settings, 'OPENAI_API_KEY', None)

class QueryAnalyzer:
    """
    사용자 질문을 분석하는 클래스
    
    이 클래스는 사용자의 질문을 분석하여 질문 유형과 관련 키워드를 추출합니다.
    LLM 기반 분석과 규칙 기반 분석을 모두 지원하며, LLM 서비스가 제공되는 경우
    LLM 기반 분석을 우선적으로 사용합니다.
    
    Attributes:
        llm_service (LLMService): LLM API 호출을 처리하는 서비스 (없으면 규칙 기반 분석만 사용)
        week_keywords (list): 임신 주차 관련 키워드 목록
        symptom_keywords (list): 증상 관련 키워드 목록
        food_keywords (list): 식품 관련 키워드 목록
        examination_keywords (list): 검사 관련 키워드 목록
        welfare_keywords (list): 복지 관련 키워드 목록
    """
    
    def __init__(self, llm_service=None):
        """
        QueryAnalyzer 초기화
        
        Args:
            llm_service (LLMService, optional): LLM API 호출을 처리하는 서비스
        """
        # LLM 서비스 설정
        self.llm_service = llm_service
        
        # 임신 주차 관련 키워드
        self.week_keywords = ["주차", "개월", "주", "개월차", "몇 주", "몇 개월"]
        
        # 증상 관련 키워드
        self.symptom_keywords = ["아파요", "통증", "불편", "증상", "느껴요",
                               "저려요", "붓고", "메스꺼움", "구토", "불면", "입덧"]
        
        # 식품 관련 키워드
        self.food_keywords = ["먹어도", "음식", "식품", "식이", "섭취",
                            "음료", "마셔도", "식단", "영양"]
        
        # 검사 관련 키워드
        self.examination_keywords = ["검사", "진단", "촬영", "초음파", "소변검사"]
        
        # 복지 관련 키워드
        self.welfare_keywords = ["지원", "혜택", "카드", "보험", "복지"]
    
    def analyze(self, user_query):
        """
        사용자 질문 분석하여 질문 유형과 관련 키워드 추출
        
        Args:
            user_query (str): 사용자 질문 내용
            
        Returns:
            dict: 분석 결과 딕셔너리
                {
                    "query_type": "질문 유형",
                    "keywords": {"키워드1": "값1", "키워드2": "값2", ...},
                    "explanation": "분류 이유 설명"
                }
        """
        # LLM 서비스가 있으면 LLM 기반 분석 사용, 없으면 규칙 기반 분석 사용
        if self.llm_service:
            try:
                analysis_result = self._analyze_with_llm(user_query)
                logger.info(f"LLM 질문 분석 결과: {analysis_result}")
                return analysis_result
            except Exception as e:
                logger.error(f"LLM 질문 분석 오류, 규칙 기반 분석으로 대체: {str(e)}")
                # LLM 분석 실패 시 규칙 기반 분석으로 폴백
                return self._analyze_with_rules(user_query)
        else:
            # LLM 서비스가 없으면 규칙 기반 분석 사용
            return self._analyze_with_rules(user_query)
    
    def _analyze_with_llm(self, user_query):
        """
        LLM을 사용한 질문 분석
        
        Args:
            user_query (str): 사용자 질문 내용
            
        Returns:
            dict: LLM 분석 결과 딕셔너리
        """
        # LLM에게 질문 분석을 요청하는 프롬프트 생성
        prompt = f"""
        Analyze the following question and extract the question type and relevant keywords.
        
        Question: {user_query}
        
        Please provide your response in JSON format as follows:
        {{
            "query_type": "One of: pregnancy_week, symptom, food, examination, welfare, general",
            "keywords": {{
                "week": "Pregnancy week (number only, if present)",
                "symptom": "Symptom keyword (for symptom-related questions)",
                "food_words": ["Food-related keywords (for food-related questions)"],
                "exam_words": ["Examination-related keywords (for examination-related questions)"]
            }},
            "explanation": "Brief explanation of why this question is classified as the given type"
        }}
        
        Question type descriptions:
        - pregnancy_week: Requests for information about specific pregnancy weeks (e.g., "What changes occur at 10 weeks of pregnancy?")
        - symptom: Questions about pregnancy symptoms (e.g., "How long does morning sickness last?")
        - food: Questions about diet during pregnancy (e.g., "Can I drink coffee during pregnancy?")
        - examination: Questions about medical tests during pregnancy (e.g., "When should I get an amniocentesis?")
        - welfare: Questions about pregnancy/childbirth welfare benefits (e.g., "How can I receive pregnancy support funds?")
        - general: General questions that don't fit into the above categories
        
        Respond only with the JSON format.
        """
        
        # LLM 호출
        response = self.llm_service.call(prompt, temperature=0.1)
        
        try:
            # JSON 응답 파싱
            # 응답에서 JSON 부분만 추출 (LLM이 추가 텍스트를 반환할 수 있음)
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            
            analysis_result = json.loads(json_str)
            
            # 필수 필드 확인 및 추가
            if "query_type" not in analysis_result:
                analysis_result["query_type"] = "general"
            
            if "keywords" not in analysis_result:
                analysis_result["keywords"] = {}
            
            if "explanation" not in analysis_result:
                analysis_result["explanation"] = "분석 결과 없음"
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"LLM 응답 파싱 오류: {str(e)}")
            raise
    
    def _analyze_with_rules(self, user_query):
        """
        규칙 기반 질문 분석
        
        키워드 매칭을 통해 질문 유형을 결정하고 관련 키워드를 추출합니다.
        LLM 분석이 실패하거나 LLM 서비스가 없을 때 사용됩니다.
        
        Args:
            user_query (str): 사용자 질문 내용
            
        Returns:
            dict: 규칙 기반 분석 결과 딕셔너리
                {
                    "query_type": "질문 유형",
                    "keywords": {"키워드1": "값1", "키워드2": "값2", ...},
                    "explanation": "규칙 기반 분석 결과"
                }
        """
        query_type = self._determine_query_type(user_query)
        keywords = self._extract_keywords(user_query, query_type)
        
        logger.info(f"규칙 기반 질문 분석 결과: 유형={query_type}, 키워드={keywords}")
        
        return {
            "query_type": query_type,
            "keywords": keywords,
            "explanation": f"규칙 기반 분석: {query_type} 유형으로 분류됨"
        }
    
    def _determine_query_type(self, query):
        """
        질문 유형 결정
        
        키워드 매칭을 통해 질문의 유형을 결정합니다.
        
        Args:
            query (str): 사용자 질문 내용
            
        Returns:
            str: 질문 유형 (symptom, food, examination, welfare, pregnancy_week, general)
        """
        # 증상 관련 키워드가 있는지 먼저 확인
        if any(kw in query for kw in self.symptom_keywords):
            return "symptom"
        # 식품 관련 키워드가 있는지 확인
        elif any(kw in query for kw in self.food_keywords):
            return "food"
        # 검사 관련 키워드가 있는지 확인
        elif any(kw in query for kw in self.examination_keywords):
            return "examination"
        # 복지 관련 키워드가 있는지 확인
        elif any(kw in query for kw in self.welfare_keywords):
            return "welfare"
        # 주차 관련 키워드가 있는지 확인
        elif any(kw in query for kw in self.week_keywords):
            return "pregnancy_week"
        # 위의 모든 경우에 해당하지 않으면 일반 질문으로 분류
        else:
            return "general"
    
    def _extract_keywords(self, query, query_type):
        """
        질문 유형에 따라 관련 키워드 추출
        
        질문 내용에서 유형에 맞는 키워드를 추출합니다.
        예를 들어, 임신 주차 관련 질문에서는 주차 정보를,
        증상 관련 질문에서는 증상 키워드를 추출합니다.
        
        Args:
            query (str): 사용자 질문 내용
            query_type (str): 질문 유형
            
        Returns:
            dict: 추출된 키워드 딕셔너리
        """
        keywords = {}
        
        # 주차 정보 추출 (모든 질문 유형에서 공통으로 수행)
        numbers = re.findall(r'\d+', query)
        if numbers and any(kw in query for kw in self.week_keywords):
            # 개월 단위인 경우 주차로 변환
            if "개월" in query:
                # 개월을 주차로 변환 (대략적으로)
                weeks = int(numbers[0]) * 4
                keywords["week"] = weeks
            else:
                # 주차 단위인 경우 그대로 사용
                keywords["week"] = int(numbers[0])
        
        # 질문 유형에 따라 추가 키워드 추출
        if query_type == "symptom":
            # 증상 관련 키워드 추출
            for kw in self.symptom_keywords:
                if kw in query:
                    keywords["symptom"] = kw
                    break
        
        elif query_type == "food":
            # 식품 관련 키워드 추출
            food_words = []
            for kw in self.food_keywords:
                if kw in query:
                    food_words.append(kw)
            keywords["food_words"] = food_words
        
        elif query_type == "examination":
            # 검사 관련 키워드 추출
            exam_words = []
            for kw in self.examination_keywords:
                if kw in query:
                    exam_words.append(kw)
            keywords["exam_words"] = exam_words
        
        return keywords


class CacheManager:
    """API 응답을 캐싱하는 클래스"""
    
    def __init__(self, cache_ttl=3600):  # 기본 1시간 캐시
        self.cache_ttl = cache_ttl
        self.cache = {}
    
    def get(self, key):
        """캐시에서 값 조회"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return value
            else:
                # TTL 만료
                del self.cache[key]
        return None
    
    def set(self, key, value):
        """캐시에 값 저장"""
        self.cache[key] = (value, time.time())
    
    def clear(self):
        """캐시 전체 삭제"""
        self.cache.clear()


class LLMService:
    """
    LLM API를 호출하는 클래스
    
    이 클래스는 OpenAI API를 사용하여 LLM(대규모 언어 모델)과 통신합니다.
    질문 분석, 응답 생성 등 다양한 작업에 사용됩니다.
    
    Attributes:
        api_key (str): OpenAI API 키
        api_url (str): LLM API URL (설정된 경우)
        model (str): 사용할 LLM 모델 (기본값: gpt-4)
    """
    
    def __init__(self, api_key=None):
        """
        LLMService 초기화
        
        Args:
            api_key (str, optional): OpenAI API 키 (없으면 settings에서 가져옴)
        """
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        self.api_url = getattr(settings, 'LLM_API_URL', None)
        self.model = getattr(settings, 'LLM_MODEL', 'gpt-4')
        
        # OpenAI API 키 설정
        if self.api_key:
            openai.api_key = self.api_key
    
    def call(self, prompt, temperature=0.7, max_tokens=1000):
        """
        LLM API 호출
        
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
        
        # 실제 LLM API 연동 코드 (OpenAI API 예시)
        if not self.api_key:
            # API 키가 없으면 더미 응답 반환
            logger.warning("LLM API 키가 설정되지 않음")
            return self._dummy_response(prompt)
        
        try:
            # OpenAI API 호출
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": """You are an expert providing medically accurate information about pregnancy and childbirth.
                    Always respond in a friendly and clear manner.
                    
                    Follow these guidelines for your responses:
                    1. All information should be based on the latest medical research and guidelines.
                    2. Always structure your response in the following sections:
                       - Overview (brief summary of the question)
                       - Detailed information (providing relevant medical information)
                       - Recommendations (providing practical advice)
                       - Cautions (if necessary)
                    3. For serious medical symptoms, always recommend consulting with a doctor.
                    4. Do not provide uncertain information, only provide information you are confident about.
                    5. Respond in the same language as the user's query.
                    """},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM API 호출 오류: {str(e)}")
            # 언어 감지하여 해당 언어로 오류 메시지 반환
            is_korean = any(char in prompt for char in "가나다라마바사아자차카타파하")
            if is_korean:
                return "죄송합니다. 현재 서비스에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
            else:
                return "Sorry, there was a temporary issue with the service. Please try again later."
    
    def _dummy_response(self, prompt):
        """
        API 키가 없을 때 사용하는 더미 응답 생성
        
        Args:
            prompt (str): 사용자 프롬프트
            
        Returns:
            str: 더미 응답 텍스트
        """
        # 언어 감지
        is_korean = any(char in prompt for char in "가나다라마바사아자차카타파하")
        
        # 한국어/영어 더미 응답
        if is_korean:
            return """
            [개발 모드 응답]
            
            안녕하세요! 현재 개발 모드에서 실행 중입니다. 실제 API 키가 설정되지 않아 테스트 응답을 제공합니다.
            
            질문에 대한 답변:
            임신 중에는 균형 잡힌 식단과 충분한 휴식이 중요합니다. 정기적인 산부인과 검진을 통해 건강 상태를 확인하세요.
            
            추가 질문이 있으시면 언제든지 물어보세요!
            """
        else:
            return """
            [Development Mode Response]
            
            Hello! This is running in development mode. No actual API key is set, so I'm providing a test response.
            
            Answer to your question:
            During pregnancy, a balanced diet and sufficient rest are important. Regular check-ups with your obstetrician are recommended to monitor your health.
            
            Feel free to ask if you have any more questions!
            """


class ResponseGenerator:
    """
    API 결과를 기반으로 응답을 생성하는 클래스
    
    이 클래스는 질문 분석 결과를 바탕으로 적절한 응답을 생성합니다.
    질문 유형에 따라 다른 응답 템플릿을 사용하며, LLM 서비스를 통해
    자연스러운 응답을 생성합니다.
    
    Attributes:
        llm_service (LLMService): LLM API 호출을 처리하는 서비스
    """
    
    def __init__(self, llm_service=None):
        """
        ResponseGenerator 초기화
        
        Args:
            llm_service (LLMService, optional): LLM API 호출을 처리하는 서비스
        """
        self.llm_service = llm_service or LLMService()
    
    def generate_response(self, query_info):
        """
        질문 분석 결과에서 응답 생성
        
        질문 유형에 따라 적절한 응답 생성 메서드를 호출합니다.
        
        Args:
            query_info (dict): 질문 분석 결과 딕셔너리
                {
                    "query_type": "질문 유형",
                    "keywords": {"키워드1": "값1", "키워드2": "값2", ...},
                    "explanation": "분류 이유 설명"
                }
                
        Returns:
            str: 생성된 응답 텍스트
        """
        
        # 질문 유형에 따라 다른 프롬프트 템플릿 사용
        if query_info["query_type"] == "pregnancy_week":
            return self._generate_week_info_response(query_info)
        elif query_info["query_type"] == "symptom":
            return self._generate_symptom_response(query_info)
        elif query_info["query_type"] == "food":
            return self._generate_food_response(query_info)
        else:
            return self._generate_general_response(query_info)
    
    def _generate_week_info_response(self, query_info):
        """
        임신 주차 정보 응답 생성
        
        Args:
            query_info (dict): 질문 분석 결과 딕셔너리
            
        Returns:
            str: 임신 주차 정보 응답
        """
        
        # Extract data needed for response
        week = query_info["keywords"].get("week", "unknown")
        
        # Create prompt
        prompt = f"""
        임신 {week}주차에 대한 정보를 제공해주세요. 다음 내용을 포함해주세요:
        
        1. 태아 발달 상태
        2. 산모의 신체 변화
        3. 이 시기에 주의해야 할 점
        4. 권장되는 검사나 영양 섭취
        
        정확하고 의학적으로 검증된 정보만 제공해주세요.
        """
        
        # Call LLM service
        try:
            response = self.llm_service.call(prompt, temperature=0.3)
            return response
        except Exception as e:
            logger.error(f"임신 주차 정보 응답 생성 오류: {str(e)}")
            return self._fallback_response("week_info", week)
    
    def _generate_symptom_response(self, query_info):
        """
        증상 관련 응답 생성
        
        Args:
            query_info (dict): 질문 분석 결과 딕셔너리
            
        Returns:
            str: 증상 관련 응답
        """
        
        # Extract symptom information
        symptom = query_info["keywords"].get("symptom", "")
        week = query_info["keywords"].get("week", "")
        
        # Create prompt
        prompt = f"""
        임신 중 '{symptom}' 증상에 대한 정보를 제공해주세요. 다음 내용을 포함해주세요:
        
        1. 증상의 원인
        2. 일반적인 대처 방법
        3. 의사와 상담이 필요한 경우
        4. 완화를 위한 생활 습관 조언
        
        {f'임신 {week}주차와 관련된 정보도 포함해주세요.' if week else ''}
        
        정확하고 의학적으로 검증된 정보만 제공해주세요.
        """
        
        # Call LLM service
        try:
            response = self.llm_service.call(prompt, temperature=0.3)
            return response
        except Exception as e:
            logger.error(f"증상 관련 응답 생성 오류: {str(e)}")
            return self._fallback_response("symptom", symptom)
    
    def _generate_food_response(self, query_info):
        """
        식품 관련 응답 생성
        
        Args:
            query_info (dict): 질문 분석 결과 딕셔너리
            
        Returns:
            str: 식품 관련 응답
        """
        
        # Extract food information
        food_words = query_info["keywords"].get("food_words", [])
        food_str = ", ".join(food_words) if food_words else "음식"
        week = query_info["keywords"].get("week", "")
        
        # Create prompt
        prompt = f"""
        임신 중 '{food_str}'에 관한 정보를 제공해주세요. 다음 내용을 포함해주세요:
        
        1. 임신 중 섭취 안전성
        2. 영양학적 가치와 이점
        3. 섭취 시 주의사항
        4. 권장 섭취량 또는 대체 식품
        
        {f'임신 {week}주차와 관련된 정보도 포함해주세요.' if week else ''}
        
        정확하고 의학적으로 검증된 정보만 제공해주세요.
        """
        
        # Call LLM service
        try:
            response = self.llm_service.call(prompt, temperature=0.3)
            return response
        except Exception as e:
            logger.error(f"식품 관련 응답 생성 오류: {str(e)}")
            return self._fallback_response("food", food_str)
    
    def _generate_general_response(self, query_info):
        """
        일반 질문에 대한 응답 생성
        
        Args:
            query_info (dict): 질문 분석 결과 딕셔너리
            
        Returns:
            str: 일반 질문 응답
        """
        
        # Extract query type and original query
        query_type = query_info["query_type"]
        original_query = query_info.get("original_query", "")
        
        # Create prompt
        prompt = f"""
        다음 임신 관련 질문에 대해 답변해주세요:
        
        질문: {original_query}
        
        질문 유형: {query_type}
        
        정확하고 의학적으로 검증된 정보만 제공해주세요.
        """
        
        # Call LLM service
        try:
            response = self.llm_service.call(prompt, temperature=0.5)
            return response
        except Exception as e:
            logger.error(f"일반 응답 생성 오류: {str(e)}")
            return self._fallback_response("general", query_type)
    
    def _fallback_response(self, response_type, keyword=""):
        """
        오류 발생 시 폴백 응답 생성
        
        Args:
            response_type (str): 응답 유형
            keyword (str, optional): 관련 키워드
            
        Returns:
            str: 폴백 응답 텍스트
        """
        # 한국어 폴백 응답
        if response_type == "week_info":
            return f"임신 {keyword}주차에 대한 정보를 제공해 드리려 했으나, 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
        elif response_type == "symptom":
            return f"'{keyword}' 증상에 대한 정보를 제공해 드리려 했으나, 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
        elif response_type == "food":
            return f"'{keyword}'에 관한 정보를 제공해 드리려 했으나, 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
        else:
            return "질문에 대한 답변을 생성하는 중 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    
    def generate_follow_up_questions(self, query_info):
        """
        후속 질문 생성
        
        Args:
            query_info (dict): 질문 분석 결과 딕셔너리
            
        Returns:
            list: 후속 질문 목록
        """
        # 질문 유형에 따라 다른 후속 질문 생성
        query_type = query_info["query_type"]
        
        if query_type == "pregnancy_week":
            week = query_info["keywords"].get("week", "")
            if week:
                return [
                    f"{week}주차에 필요한 영양소는 무엇인가요?",
                    f"{week}주차에 받아야 할 검사가 있나요?",
                    f"{week}주차에 주의해야 할 증상이 있나요?"
                ]
        
        elif query_type == "symptom":
            symptom = query_info["keywords"].get("symptom", "")
            if symptom:
                return [
                    f"{symptom} 증상은 언제까지 지속되나요?",
                    f"{symptom} 증상을 완화하는 방법이 있나요?",
                    f"{symptom} 증상이 심할 때는 어떻게 해야 하나요?"
                ]
        
        elif query_type == "food":
            food_words = query_info["keywords"].get("food_words", [])
            if food_words:
                food = food_words[0] if food_words else "음식"
                return [
                    f"임신 중 {food} 대신 먹을 수 있는 대체 식품은 무엇인가요?",
                    f"{food}의 적정 섭취량은 얼마인가요?",
                    f"{food}에 포함된 영양소는 무엇인가요?"
                ]
        
        # 기본 후속 질문
        return [
            "임신 중 영양 관리는 어떻게 해야 하나요?",
            "임신 중 운동은 어떻게 해야 하나요?",
            "정기 검진은 언제 받아야 하나요?"
        ]


class MaternalHealthLLMService:
    """
    산모 대상 LLM 서비스 메인 클래스
    
    이 클래스는 산모 건강 관련 질문을 처리하고 응답을 생성하는 메인 서비스입니다.
    사용자 질문을 분석하고, 적절한 응답과 후속 질문을 생성합니다.
    
    Attributes:
        llm_service (LLMService): LLM API 호출을 처리하는 서비스
        query_analyzer (QueryAnalyzer): 사용자 질문을 분석하는 컴포넌트
        response_generator (ResponseGenerator): 응답을 생성하는 컴포넌트
    """
    
    def __init__(self):
        """
        MaternalHealthLLMService 초기화
        
        LLM 서비스, 질문 분석기, 응답 생성기 인스턴스를 생성합니다.
        """
        # LLM 서비스 인스턴스 생성
        self.llm_service = LLMService()
        # LLM 서비스를 QueryAnalyzer에 전달하여 LLM 기반 분석 활성화
        self.query_analyzer = QueryAnalyzer(self.llm_service)
        self.response_generator = ResponseGenerator(self.llm_service)
    
    def process_query(self, user_id, query_text, user_info=None):
        """
        사용자 질문 처리 및 응답 생성
        
        Args:
            user_id (str): 사용자 UUID
            query_text (str): 사용자 질문 내용
            user_info (dict, optional): 사용자 정보 (이름, 임신 여부, 임신 주차 등)
            
        Returns:
            dict: 응답 결과 딕셔너리
                {
                    "response": "LLM 응답 내용",
                    "follow_up_questions": ["후속 질문1", "후속 질문2", ...],
                    "query_info": {
                        "query_type": "질문 유형",
                        "keywords": {"키워드1": "값1", "키워드2": "값2", ...}
                    }
                }
        """
        
        # 1. 질문 분석 (LLM 기반 분석 사용)
        query_info = self.query_analyzer.analyze(query_text)
        
        # 2. 사용자 정보 통합 (있는 경우)
        if user_info and "pregnancy_week" in user_info and "week" not in query_info["keywords"]:
            query_info["keywords"]["week"] = user_info["pregnancy_week"]
        
        # 3. 응답 생성
        response_text = self.response_generator.generate_response(query_info)
        
        # 4. 후속 질문 생성
        follow_up_questions = self.response_generator.generate_follow_up_questions(query_info)
        
        # 5. 언어 감지 및 후속 질문 번역 (필요한 경우)
        # 한국어 질문인 경우 한국어 후속 질문 유지, 영어 질문인 경우 영어 후속 질문 생성
        is_korean = any(char in query_text for char in "가나다라마바사아자차카타파하")
        
        if not is_korean and follow_up_questions:
            # 영어 질문에 대해 영어 후속 질문 생성
            english_follow_ups = [
                "Can I get more detailed information?",
                "Can I get contact information for the relevant department?",
                "What welfare benefits are available related to this?"
            ]
            follow_up_questions = english_follow_ups
        
        return {
            "response": response_text,
            "follow_up_questions": follow_up_questions,
            "query_info": query_info
        } 