import re
import logging
import requests
from functools import lru_cache
import time
import json
from django.conf import settings

# 로깅 설정
logger = logging.getLogger(__name__)

class QueryAnalyzer:
    """사용자 질문을 분석하는 클래스"""
    
    def __init__(self):
        # 임신 주차 관련 키워드
        self.week_keywords = ["주차", "개월", "주", "개월차", "임신"]
        
        # 증상 관련 키워드
        self.symptom_keywords = ["아파요", "통증", "불편", "증상", "느껴요",
                               "저려요", "붓고", "메스꺼움", "구토", "불면"]
        
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
        if any(kw in query for kw in self.week_keywords):
            return "pregnancy_week"
        elif any(kw in query for kw in self.symptom_keywords):
            return "symptom"
        elif any(kw in query for kw in self.food_keywords):
            return "food"
        elif any(kw in query for kw in self.examination_keywords):
            return "examination"
        elif any(kw in query for kw in self.welfare_keywords):
            return "welfare"
        else:
            return "general"
    
    def _extract_keywords(self, query, query_type):
        """질문 유형에 따라 관련 키워드 추출"""
        keywords = {}
        
        if query_type == "pregnancy_week":
            # 정규 표현식으로 숫자 추출
            numbers = re.findall(r'\d+', query)
            if numbers:
                # 주차 또는 개월 단위로 변환
                if "개월" in query:
                    # 개월을 주차로 변환 (대략적으로)
                    weeks = int(numbers[0]) * 4
                    keywords["week"] = weeks
                else:
                    keywords["week"] = int(numbers[0])
        
        # 증상 키워드 추출
        elif query_type == "symptom":
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


class FlorenceAPIManager:
    """Florence API를 호출하는 클래스"""
    
    def __init__(self, base_url=None):
        self.base_url = base_url or getattr(settings, 'FLORENCE_API_URL', 'http://localhost:8000/v1/rag/')
        self.rdf_file = getattr(settings, 'FLORENCE_RDF_FILE', 'data/rdf/wellness.n-triples')
        self.format = getattr(settings, 'FLORENCE_RDF_FORMAT', 'nt')
        self.cache = CacheManager()
        
        # 주차와 URI 매핑
        self.week_uri_mapping = self._init_week_uri_mapping()
    
    def _init_week_uri_mapping(self):
        """주차와 URI 매핑 초기화"""
        # 실제로는 DB에서 가져오거나, API를 호출하여 동적으로 구성할 수 있음
        # 여기서는 예시로 하드코딩
        return {
            28: "http://www.wellness.ai/resource/02-016",
            # 다른 주차별 URI 매핑...
        }
    
    def get_pregnancy_week_info(self, week):
        """임신 주차 정보 조회 (캐싱 적용)"""
        cache_key = f"pregnancy_week_{week}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            logger.info(f"캐시에서 주차 정보 조회: {week}주차")
            return cached_result
        
        # 주차에 맞는 리소스 URI 찾기
        resource_uri = self._get_resource_uri_for_week(week)
        if not resource_uri:
            logger.warning(f"주차에 맞는 URI를 찾을 수 없음: {week}주차")
            return None
        
        # 리소스 정보 요약 조회
        summary_results = self._call_resource_summary(resource_uri)
        
        # 리소스 관계 정보 조회
        relations_results = self._call_resource_relations(resource_uri)
        
        result = {
            "summary": summary_results,
            "relations": relations_results,
            "resource_uri": resource_uri,
            "week": week
        }
        
        # 결과 캐싱
        self.cache.set(cache_key, result)
        
        return result
    
    def search_by_keyword(self, keyword):
        """키워드 검색"""
        cache_key = f"keyword_{keyword}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            logger.info(f"캐시에서 키워드 검색 결과 조회: {keyword}")
            return cached_result
        
        result = self._call_keyword_search(keyword)
        
        # 결과 캐싱
        self.cache.set(cache_key, result)
        
        return result
    
    def get_disease_info(self, disease_uri):
        """질병 정보 조회"""
        cache_key = f"disease_{disease_uri}"
        cached_result = self.cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        result = self._call_resource_relations(disease_uri, depth=2)
        
        # 결과 캐싱
        self.cache.set(cache_key, result)
        
        return result
    
    def _get_resource_uri_for_week(self, week):
        """주차에 맞는 리소스 URI 반환"""
        # 캐시된 매핑에서 가져오기
        return self.week_uri_mapping.get(week)
    
    def _call_resource_summary(self, resource_uri):
        """리소스 요약 정보 API 호출"""
        url = f"{self.base_url}rdf-analysis/"
        payload = {
            "action": "resource_summary",
            "resource_uri": resource_uri,
            "rdf_file": self.rdf_file,
            "format": self.format
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"리소스 요약 API 호출 오류: {str(e)}")
            return {"error": str(e)}
    
    def _call_resource_relations(self, resource_uri, depth=1):
        """리소스 관계 정보 API 호출"""
        url = f"{self.base_url}rdf-analysis/"
        payload = {
            "action": "resource_relations",
            "resource_uri": resource_uri,
            "depth": depth,
            "rdf_file": self.rdf_file,
            "format": self.format
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"리소스 관계 API 호출 오류: {str(e)}")
            return {"error": str(e)}
    
    def _call_keyword_search(self, keyword):
        """키워드 검색 API 호출"""
        url = f"{self.base_url}rdf-analysis/"
        payload = {
            "action": "keyword_search",
            "keyword": keyword,
            "rdf_file": self.rdf_file,
            "format": self.format
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"키워드 검색 API 호출 오류: {str(e)}")
            return {"error": str(e)}


class LLMService:
    """LLM API를 호출하는 클래스"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or getattr(settings, 'LLM_API_KEY', None)
        self.api_url = getattr(settings, 'LLM_API_URL', None)
        self.model = getattr(settings, 'LLM_MODEL', 'gpt-4')
    
    def call(self, prompt, temperature=0.7, max_tokens=1000):
        """LLM API 호출"""
        logger.info(f"LLM API 호출: {prompt[:50]}...")
        
        # 실제 LLM API 연동 코드 (OpenAI API 예시)
        if not self.api_url or not self.api_key:
            # API 키나 URL이 없으면 더미 응답 반환
            logger.warning("LLM API 키 또는 URL이 설정되지 않음")
            return self._dummy_response(prompt)
        
        try:
            # 여기에 실제 LLM API 호출 코드 작성
            # OpenAI API 예시
            # response = openai.Completion.create(
            #     model=self.model,
            #     prompt=prompt,
            #     temperature=temperature,
            #     max_tokens=max_tokens
            # )
            # return response.choices[0].text.strip()
            
            # 임시로 더미 응답 반환
            return self._dummy_response(prompt)
            
        except Exception as e:
            logger.error(f"LLM API 호출 오류: {str(e)}")
            return f"죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요. (오류: {str(e)})"
    
    def _dummy_response(self, prompt):
        """테스트용 더미 응답"""
        if "임신" in prompt and any(str(week) in prompt for week in range(1, 41)):
            return """
            안녕하세요! 요청하신 임신 정보에 대해 알려드립니다.
            
            [태아 발달]
            이 시기에는 태아의 뇌가 발달하고, 감각 기관이 형성됩니다. 
            
            [산모 변화]
            피로감, 소화불량 등이 나타날 수 있으며, 적절한 휴식이 필요합니다.
            
            [생활 수칙]
            균형 잡힌 식단과 적절한 운동을 유지하세요. 정기 검진을 꼭 받으시기 바랍니다.
            
            무엇이든 더 궁금한 점이 있으시면 질문해주세요!
            """
        elif any(keyword in prompt for keyword in ["메스꺼움", "구토", "입덧"]):
            return """
            입덧은 임신 초기에 흔히 나타나는 증상입니다. 다음과 같은 방법으로 증상을 완화할 수 있습니다:
            
            1. 소량씩 자주 먹기
            2. 아침에 일어나자마자 크래커 등 가벼운 음식 섭취
            3. 생강차나 페퍼민트 차 마시기
            4. 충분한 수분 섭취
            
            입덧이 심하다면 의사와 상담하는 것이 좋습니다.
            """
        else:
            return """
            안녕하세요! 산모 건강 도우미입니다. 
            
            임신 주차별 정보, 증상, 식이요법, 운동, 검사 일정 등에 대해 질문해주시면 
            정확한 정보를 제공해드리겠습니다.
            
            예를 들어, "임신 28주에는 어떤 검사를 받아야 하나요?" 또는 
            "임신 중 허리 통증은 어떻게 관리해야 하나요?" 등의 질문을 해주세요.
            """


class ResponseGenerator:
    """API 결과를 기반으로 응답을 생성하는 클래스"""
    
    def __init__(self, llm_service=None):
        self.llm_service = llm_service or LLMService()
    
    def generate_response(self, analysis_results, query_info):
        """API 분석 결과에서 응답 생성"""
        
        # 질문 유형에 따라 다른 프롬프트 템플릿 사용
        if query_info["query_type"] == "pregnancy_week":
            return self._generate_week_info_response(analysis_results, query_info)
        elif query_info["query_type"] == "symptom":
            return self._generate_symptom_response(analysis_results, query_info)
        elif query_info["query_type"] == "food":
            return self._generate_food_response(analysis_results, query_info)
        else:
            return self._generate_general_response(analysis_results, query_info)
    
    def _generate_week_info_response(self, analysis_results, query_info):
        """임신 주차 정보 응답 생성"""
        
        # 응답에 필요한 데이터 추출
        week = query_info["keywords"].get("week", "알 수 없는")
        
        summary = analysis_results.get("summary", {})
        resource_label = summary.get("resource_label", f"임신 {week}주차")
        
        relations = analysis_results.get("relations", {})
        relation_groups = relations.get("relation_groups", {})
        
        # 태아 발달 정보
        fetal_dev = []
        if "태아발달" in relation_groups:
            fetal_dev = [item["target_label"] for item in relation_groups["태아발달"]]
        
        # 신체 변화 정보
        body_changes = []
        if "신체변화" in relation_groups:
            body_changes = [item["target_label"] for item in relation_groups["신체변화"]]
        
        # 생활 수칙
        living_rules = []
        if "생활수칙" in relation_groups:
            living_rules = [item["target_label"] for item in relation_groups["생활수칙"]]
        
        # 권장 식품
        recommended_foods = []
        if "권장식품" in relation_groups:
            recommended_foods = [item["target_label"] for item in relation_groups["권장식품"]][:5]  # 상위 5개만
        
        # 검사 종류
        examinations = []
        if "검사종류" in relation_groups:
            examinations = [item["target_label"] for item in relation_groups["검사종류"]]
        
        # 프롬프트 생성
        prompt = f"""
        당신은 의학적으로 정확한 임신 관련 정보를 제공하는 전문가입니다.
        
        임신 {week}주차에 대한 다음 정보를 바탕으로, 이 시기의 태아 발달, 산모의 신체 변화, 
        생활 수칙, 권장 식품, 필요한 검사 등에 대해 산모에게 친절하고 명확하게 안내해주세요.
        
        [태아 발달]
        {', '.join(fetal_dev)}
        
        [신체 변화]
        {', '.join(body_changes)}
        
        [생활 수칙]
        {', '.join(living_rules)}
        
        [권장 식품]
        {', '.join(recommended_foods)}
        
        [필요한 검사]
        {', '.join(examinations)}
        
        질문: {query_info["original_query"]}
        """
        
        # LLM 호출
        response = self.llm_service.call(prompt)
        
        return response
    
    def _generate_symptom_response(self, analysis_results, query_info):
        """증상 관련 응답 생성"""
        symptom = query_info["keywords"].get("symptom", "")
        symptom_words = query_info["keywords"].get("symptom_words", [])
        
        symptom_info = []
        if "symptom_search" in analysis_results:
            search_results = analysis_results["symptom_search"].get("results", [])
            for result in search_results[:5]:  # 상위 5개 결과만 사용
                symptom_info.append(result.get("text", ""))
        
        # 현재 임신 주차 정보
        week_info = {}
        if "week_info" in analysis_results:
            relations = analysis_results["week_info"].get("relations", {})
            relation_groups = relations.get("relation_groups", {})
            
            # 관련 질병
            diseases = []
            if "관련질병" in relation_groups:
                diseases = [item["target_label"] for item in relation_groups["관련질병"]]
            
            # 상태
            states = []
            if "상태" in relation_groups:
                states = [item["target_label"] for item in relation_groups["상태"]]
            
            week_info = {
                "week": analysis_results["week_info"].get("week", ""),
                "diseases": diseases,
                "states": states
            }
        
        # 프롬프트 생성
        prompt = f"""
        당신은 의학적으로 정확한 임신 관련 정보를 제공하는 전문가입니다.
        
        다음 정보를 바탕으로, 사용자가 질문한 '{symptom if symptom else ' '.join(symptom_words)}'에 대해
        친절하게 답변해주세요.
        
        [검색 결과]
        {chr(10).join(symptom_info)}
        
        """
        
        if week_info:
            prompt += f"""
            [임신 {week_info['week']}주차 관련 정보]
            관련 질병: {', '.join(week_info['diseases'])}
            상태: {', '.join(week_info['states'])}
            """
        
        prompt += f"""
        질문: {query_info["original_query"]}
        
        항상 의학적으로 정확한 정보를 제공하고, 심각한 증상의 경우 의사와 상담하도록 권고해주세요.
        """
        
        # LLM 호출
        response = self.llm_service.call(prompt)
        
        return response
    
    def _generate_food_response(self, analysis_results, query_info):
        """식품 관련 응답 생성"""
        food_words = query_info["keywords"].get("food_words", [])
        
        food_info = {}
        if "food_info" in analysis_results:
            food_info = analysis_results["food_info"]
        
        # 프롬프트 생성
        prompt = f"""
        당신은 의학적으로 정확한 임신 관련 정보를 제공하는 전문가입니다.
        
        다음 정보를 바탕으로, 사용자가 질문한 식품 관련 질문 '{' '.join(food_words)}'에 대해
        친절하게 답변해주세요.
        """
        
        if "recommended" in food_info:
            prompt += f"""
            [권장 식품]
            {', '.join([item["target_label"] for item in food_info["recommended"]])}
            """
        
        if "avoid" in food_info:
            prompt += f"""
            [기피 식품]
            {', '.join([item["target_label"] for item in food_info["avoid"]])}
            """
        
        if "harmful" in food_info:
            prompt += f"""
            [해로운 음식]
            {', '.join([item["target_label"] for item in food_info["harmful"]])}
            """
        
        prompt += f"""
        질문: {query_info["original_query"]}
        
        식품에 관한 일반적인 지침뿐만 아니라, 가능하다면 질문한 특정 식품에 대해서도 답변해주세요.
        임신 중 균형 잡힌 영양 섭취의 중요성을 강조해주세요.
        """
        
        # LLM 호출
        response = self.llm_service.call(prompt)
        
        return response
    
    def _generate_general_response(self, analysis_results, query_info):
        """일반 질문에 대한 응답 생성"""
        prompt = f"""
        당신은 의학적으로 정확한 임신 관련 정보를 제공하는 전문가입니다.
        
        다음 질문에 친절하게 답변해주세요:
        
        {query_info["original_query"]}
        
        임신과 관련된 정확한 정보를 제공하고, 필요하다면 의사와 상담하도록 권고해주세요.
        질문의 맥락이 명확하지 않다면, 임신 주차나 증상 등 추가 정보를 요청해도 좋습니다.
        """
        
        # LLM 호출
        response = self.llm_service.call(prompt)
        
        return response
    
    def generate_follow_up_questions(self, analysis_results, query_info):
        """컨텍스트에 맞는 후속 질문 제안"""
        
        follow_ups = []
        
        if query_info["query_type"] == "pregnancy_week":
            week = query_info["keywords"].get("week")
            
            # 관련 질병이 있으면 질병 관련 질문 제안
            if "relations" in analysis_results and "relation_groups" in analysis_results["relations"]:
                if "관련질병" in analysis_results["relations"]["relation_groups"]:
                    diseases = analysis_results["relations"]["relation_groups"]["관련질병"]
                    if diseases:
                        disease = diseases[0]["target_label"]
                        follow_ups.append(f"{disease}은 어떤 증상이 있나요?")
            
            # 검사 관련 질문
            follow_ups.append(f"임신 {week}주에 꼭 받아야 하는 검사는 무엇인가요?")
            
            # 식이 관련 질문
            follow_ups.append(f"임신 {week}주에 좋은 영양제는 무엇인가요?")
        
        elif query_info["query_type"] == "symptom":
            # 증상 관련 후속 질문
            follow_ups.append("이 증상이 위험한가요?")
            follow_ups.append("언제 병원에 가야 하나요?")
            follow_ups.append("이 증상을 완화하는 방법이 있나요?")
        
        elif query_info["query_type"] == "food":
            # 식품 관련 후속 질문
            follow_ups.append("임신 중에 어떤 영양소가 특히 중요한가요?")
            follow_ups.append("입덧이 심할 때 먹기 좋은 음식은 무엇인가요?")
            follow_ups.append("임신 중에 꼭 피해야 하는 음식은 무엇인가요?")
        
        else:
            # 일반적인 후속 질문
            follow_ups.append("임신 중 건강한 체중 관리는 어떻게 하나요?")
            follow_ups.append("임신 중 안전한 운동 방법은 무엇인가요?")
            follow_ups.append("출산 준비는 언제부터 시작해야 하나요?")
        
        return follow_ups[:3]  # 최대 3개만 반환


class MaternalHealthLLMService:
    """산모 대상 LLM 서비스 메인 클래스"""
    
    def __init__(self):
        self.query_analyzer = QueryAnalyzer()
        self.api_manager = FlorenceAPIManager()
        self.response_generator = ResponseGenerator(LLMService())
    
    def process_query(self, user_id, query_text, user_info=None):
        """사용자 질문 처리 및 응답 생성"""
        
        # 1. 질문 분석
        query_info = self.query_analyzer.analyze(query_text)
        
        # 2. 사용자 정보 통합 (있는 경우)
        if user_info and "pregnancy_week" in user_info and "week" not in query_info["keywords"]:
            query_info["keywords"]["week"] = user_info["pregnancy_week"]
        
        # 3. API 호출 및 데이터 수집
        analysis_results = self._collect_data_for_query(query_info)
        
        # 4. 응답 생성
        response_text = self.response_generator.generate_response(analysis_results, query_info)
        
        # 5. 후속 질문 생성
        follow_up_questions = self.response_generator.generate_follow_up_questions(analysis_results, query_info)
        
        return {
            "response": response_text,
            "follow_up_questions": follow_up_questions,
            "query_info": query_info,
            "analysis_results": analysis_results
        }
    
    def _collect_data_for_query(self, query_info):
        """쿼리 유형에 따라 필요한 API 호출 수행"""
        
        results = {}
        
        if query_info["query_type"] == "pregnancy_week":
            week = query_info["keywords"].get("week")
            if week:
                results = self.api_manager.get_pregnancy_week_info(week)
        
        elif query_info["query_type"] == "symptom":
            # 증상 키워드로 검색
            symptom = query_info["keywords"].get("symptom", "")
            if symptom:
                results["symptom_search"] = self.api_manager.search_by_keyword(symptom)
            
            symptom_words = query_info["keywords"].get("symptom_words", [])
            for word in symptom_words:
                if len(word) > 1:
                    symptom_results = self.api_manager.search_by_keyword(word)
                    if symptom_results.get("total_results", 0) > 0:
                        results["symptom_search"] = symptom_results
                        break
            
            # 현재 임신 주차 정보도 함께 제공
            if "week" in query_info["keywords"]:
                results["week_info"] = self.api_manager.get_pregnancy_week_info(
                    query_info["keywords"]["week"]
                )
        
        elif query_info["query_type"] == "food":
            # 음식 관련 질문은 주로 현재 임신 주차의 권장/기피 식품 정보 필요
            if "week" in query_info["keywords"]:
                week_info = self.api_manager.get_pregnancy_week_info(
                    query_info["keywords"]["week"]
                )
                results["food_info"] = self._extract_food_info(week_info)
            
            # 특정 음식 검색
            food_words = query_info["keywords"].get("food_words", [])
            for word in food_words:
                if len(word) > 1:
                    food_results = self.api_manager.search_by_keyword(word)
                    if food_results.get("total_results", 0) > 0:
                        results["food_search"] = food_results
                        break
        
        return results
    
    def _extract_food_info(self, week_info):
        """주차 정보에서 식품 관련 정보만 추출"""
        food_info = {}
        
        if "relations" in week_info and "relation_groups" in week_info["relations"]:
            groups = week_info["relations"]["relation_groups"]
            
            # 권장 식품
            if "권장식품" in groups:
                food_info["recommended"] = groups["권장식품"]
            
            # 기피 식품
            if "기피식품" in groups:
                food_info["avoid"] = groups["기피식품"]
            
            # 해로운 음식
            if "해로운음식" in groups:
                food_info["harmful"] = groups["해로운음식"]
            
            # 좋은 음식
            if "좋은음식" in groups:
                food_info["good"] = groups["좋은음식"]
        
        return food_info 