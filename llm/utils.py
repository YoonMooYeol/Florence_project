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
    """사용자 질문을 분석하는 클래스"""
    
    def __init__(self):
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
        """사용자 질문 분석하여 질문 유형과 관련 키워드 추출"""
        query_type = self._determine_query_type(user_query)
        keywords = self._extract_keywords(user_query, query_type)
        
        logger.info(f"질문 분석 결과: 유형={query_type}, 키워드={keywords}")
        
        return {
            "query_type": query_type,
            "keywords": keywords,
            "original_query": user_query
        }
    
    def _determine_query_type(self, query):
        """질문 유형 결정"""
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
        """질문 유형에 따라 관련 키워드 추출"""
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
                keywords["week"] = int(numbers[0])
        
        # 증상 키워드 추출
        if query_type == "symptom":
            for symptom in self.symptom_keywords:
                if symptom in query:
                    keywords["symptom"] = symptom
                    break
                    
            # 문장에서 증상 단어 추출
            symptom_words = [word for word in query.split() 
                           if len(word) > 1 and word not in ["있어요", "해요", "했어요"]]
            if symptom_words:
                keywords["symptom_words"] = symptom_words
        
        # 음식 키워드 추출
        elif query_type == "food":
            food_words = [word for word in query.split() 
                       if len(word) > 1 and word not in ["먹어도", "되나요", "괜찮나요"]]
            if food_words:
                keywords["food_words"] = food_words
        
        # 검사 키워드 추출
        elif query_type == "examination":
            exam_words = [word for word in query.split() 
                       if len(word) > 1 and word not in ["받아야", "하나요", "해야"]]
            if exam_words:
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
    """LLM API를 호출하는 클래스"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        self.api_url = getattr(settings, 'LLM_API_URL', None)
        self.model = getattr(settings, 'LLM_MODEL', 'gpt-4')
        
        # OpenAI API 키 설정
        if self.api_key:
            openai.api_key = self.api_key
    
    def call(self, prompt, temperature=0.7, max_tokens=1000):
        """LLM API 호출"""
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
            # Detect language from the prompt to return error in the same language
            if any(char in prompt for char in "가나다라마바사아자차카타파하"):
                return f"죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (오류: {str(e)})"
            else:
                return f"Sorry, a temporary error has occurred. Please try again later. (Error: {str(e)})"
    
    def _dummy_response(self, prompt):
        """Test dummy response"""
        # Extract pregnancy week
        week_match = re.search(r'임신\s*(\d+)\s*주', prompt)
        
        if "임신" in prompt and week_match:
            week = int(week_match.group(1))
            
            # Different responses based on trimester
            if week <= 12:  # First trimester (1-12 weeks)
                return """
                Hello! Here's information about the first trimester (1-12 weeks).
                
                [Fetal Development]
                During this period, the baby's major organs and nervous system begin to form.
                The heart starts beating, and limb buds appear.
                
                [Maternal Changes]
                You may experience morning sickness, fatigue, breast tenderness, and frequent urination.
                
                [Lifestyle Guidelines]
                Folic acid intake is important, and caffeine and alcohol should be limited.
                Regular check-ups are essential.
                
                [Welfare Benefits]
                (Welfare information would be provided if available and accurate)
                
                Please feel free to ask if you have any other questions!
                """
            elif week <= 27:  # Second trimester (13-27 weeks)
                return """
                Hello! Here's information about the second trimester (13-27 weeks).
                
                [Fetal Development]
                During this period, the baby's facial features become more distinct, and fingers and toes are fully formed.
                You may start to feel movement as the baby becomes more active in the amniotic fluid.
                
                [Maternal Changes]
                Morning sickness typically decreases, energy levels improve, and your pregnancy becomes visibly noticeable.
                
                [Lifestyle Guidelines]
                Appropriate exercise and a balanced diet are important.
                Second-trimester tests will help confirm your baby's health status.
                
                Please feel free to ask if you have any other questions!
                """
            else:  # Third trimester (28-40 weeks)
                return """
                Hello! Here's information about the third trimester (28-40 weeks).
                
                [Fetal Development]
                During this period, the baby's lungs mature, and weight increases rapidly.
                Brain development is active, and preparations for birth are completed.
                
                [Maternal Changes]
                You may experience back pain, leg cramps, swelling, insomnia, and practice contractions (Braxton Hicks).
                
                [Lifestyle Guidelines]
                Get plenty of rest and start preparing for childbirth.
                Regular fetal monitoring and doctor consultations are important.
                
                Please feel free to ask if you have any other questions!
                """
        elif any(keyword in prompt for keyword in ["메스꺼움", "구토", "입덧"]):
            return """
            Morning sickness is a common symptom in early pregnancy. Here are some ways to alleviate the symptoms:
            
            1. Eat small, frequent meals
            2. Consume light foods like crackers first thing in the morning
            3. Drink ginger or peppermint tea
            4. Stay well-hydrated
            
            If morning sickness is severe, it's best to consult with your doctor.
            """
        else:
            return """
            Hello! I'm your maternal health assistant.
            
            Please ask me about pregnancy information by week, symptoms, diet, exercise, examination schedules, and more for accurate information.
            
            For example, you can ask "What tests should I have at 28 weeks of pregnancy?" or "How should I manage back pain during pregnancy?"
            """


class ResponseGenerator:
    """API 결과를 기반으로 응답을 생성하는 클래스"""
    
    def __init__(self, llm_service=None):
        self.llm_service = llm_service or LLMService()
    
    def generate_response(self, query_info):
        """질문 분석 결과에서 응답 생성"""
        
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
        """Generate response for pregnancy week information"""
        
        # Extract data needed for response
        week = query_info["keywords"].get("week", "unknown")
        
        # Create prompt
        prompt = f"""
        Please provide information about pregnancy week {week}. Structure your response based on the following:
        
        Question: {query_info["original_query"]}
        
        Please structure your response in the following format:
        1. Overview: Brief summary of pregnancy week {week}
        2. Fetal Development: Detailed information about the baby's growth and development
        3. Maternal Changes: Information about physical and emotional changes in the mother
        4. Lifestyle Management: Recommendations for diet, exercise, and habits
        5. Necessary Examinations: Information about medical tests needed during this period
        6. Precautions: Special considerations to be aware of
        
        Respond in the same language as the user's question.
        """
        
        # Call LLM
        response = self.llm_service.call(prompt)
        
        return response
    
    def _generate_symptom_response(self, query_info):
        """Generate response for symptom-related queries"""
        symptom = query_info["keywords"].get("symptom", "")
        symptom_words = query_info["keywords"].get("symptom_words", [])
        
        # Create prompt
        prompt = f"""
        Please provide information about the pregnancy symptom '{symptom if symptom else ' '.join(symptom_words)}'.
        
        Question: {query_info["original_query"]}
        
        Please structure your response in the following format:
        1. Overview: Brief explanation of the symptom
        2. Causes: Main causes of the symptom
        3. Management Methods: Ways to alleviate the symptom
        4. Medical Intervention: When medical attention is necessary
        5. Precautions: Special considerations to be aware of
        
        For serious symptoms, please advise consulting with a doctor.
        Respond in the same language as the user's question.
        """
        
        # Call LLM
        response = self.llm_service.call(prompt)
        
        return response
    
    def _generate_food_response(self, query_info):
        """Generate response for food-related queries"""
        food_words = query_info["keywords"].get("food_words", [])
        
        # Create prompt
        prompt = f"""
        Please provide information about '{' '.join(food_words)}' in relation to pregnancy diet.
        
        Question: {query_info["original_query"]}
        
        Please structure your response in the following format:
        1. Overview: Brief explanation of the food and whether it's safe during pregnancy
        2. Nutritional Information: Key nutrients in the food and their importance during pregnancy
        3. Recommended Intake: Safe amounts or frequency of consumption
        4. Alternative Foods: Suggestions for alternatives if needed
        5. Precautions: Special considerations to be aware of
        
        Please emphasize the importance of balanced nutrition during pregnancy.
        Respond in the same language as the user's question.
        """
        
        # Call LLM
        response = self.llm_service.call(prompt)
        
        return response
    
    def _generate_general_response(self, query_info):
        """Generate response for general pregnancy questions"""
        prompt = f"""
        Please answer the following pregnancy-related question:
        
        {query_info["original_query"]}
        
        Please structure your response in the following format:
        1. Overview: Brief answer to the question
        2. Detailed Information: Relevant medical information
        3. Recommendations: Practical advice
        4. Precautions: Things to be aware of, if necessary
        
        Provide accurate information related to pregnancy, and recommend consulting with a doctor if necessary.
        If the context of the question is unclear, please assume the most common situation.
        Respond in the same language as the user's question.
        """
        
        # Call LLM
        response = self.llm_service.call(prompt)
        
        return response
    
    def generate_follow_up_questions(self, query_info):
        """Generate context-appropriate follow-up questions"""
        
        # 모든 질문 유형에 대해 동일한 후속 질문 사용
        follow_ups = [
            "좀 더 자세한 내용을 알수있을까요?",
            "관련된 부서 연락처를 알수있을까요?",
            "관련된 복지는 어떤게 있을까요?"
        ]
        
        return follow_ups


class MaternalHealthLLMService:
    """산모 대상 LLM 서비스 메인 클래스"""
    
    def __init__(self):
        self.query_analyzer = QueryAnalyzer()
        self.response_generator = ResponseGenerator(LLMService())
    
    def process_query(self, user_id, query_text, user_info=None):
        """사용자 질문 처리 및 응답 생성"""
        
        # 1. 질문 분석
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