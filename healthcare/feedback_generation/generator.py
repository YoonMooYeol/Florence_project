from typing import List, Dict, Any
import os
from datetime import datetime
from openai import OpenAI
import re
from urllib.parse import quote
from firecrawl import FirecrawlApp


class FeedbackGenerator:
    """수집된 대화 데이터를 기반으로 종합적인 피드백을 생성하는 클래스"""

    def __init__(self, client: OpenAI = None):
        """
        피드백 생성기 초기화

        Args:
            client: OpenAI 클라이언트. None인 경우 자동으로 생성
        """
        self.client = client if client else OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"  # 기본 모델 설정

    def generate_feedback(
        self, interactions: List[Dict[str, Any]], medical_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """대화 상호작용을 기반으로 피드백을 생성합니다.

        Args:
            interactions: 대화 상호작용 데이터 리스트
            medical_info: 외부에서 제공된 의료 정보 (선택적)

        Returns:
            피드백 결과 딕셔너리
        """
        if not interactions:
            return {
                "summary": "충분한 데이터가 없습니다.",
                "mood_analysis": "데이터 없음",
                "recommendations": [],
                "precautions": [],
                "medical_tips": [],
                "sources": [],
            }

        # 1. 기본 피드백 생성
        basic_feedback = self._generate_basic_feedback(interactions)

        # 2. 의료 정보가 제공되지 않은 경우 크롤링을 통해 정보 수집
        if not medical_info:
            try:
                # 대화 내용에서 키워드 추출
                keywords = self._extract_keywords(interactions)
                print(f"추출된 키워드: {keywords}")
                
                # 추출한 키워드로 의료 정보 크롤링
                medical_info = self._crawl_medical_info(keywords)
                print(f"크롤링 된 의료 정보: {len(medical_info.get('tips', []))}개의 팁")
            except Exception as e:
                print(f"의료 정보 수집 중 오류 발생: {e}")
                medical_info = self._get_default_medical_info()
                
        # 권장사항을 일반 텍스트로 변환
        recommendations = basic_feedback.get("recommendations", ["맞춤형 권장사항을 생성할 수 없습니다."])
        text_recommendations = []
        
        for rec in recommendations:
            # 마크다운 형식 제거
            clean_rec = rec
            # 마크다운 링크 변환 [텍스트](URL) -> 텍스트
            clean_rec = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean_rec)
            # 마크다운 강조 제거
            clean_rec = re.sub(r'\*\*([^*]+)\*\*', r'\1', clean_rec)
            clean_rec = re.sub(r'__([^_]+)__', r'\1', clean_rec)
            clean_rec = re.sub(r'\*([^*]+)\*', r'\1', clean_rec)
            clean_rec = re.sub(r'_([^_]+)_', r'\1', clean_rec)
            # 불필요한 기호 제거
            clean_rec = clean_rec.lstrip('-*•·').strip()
            
            if clean_rec:
                text_recommendations.append(clean_rec)

        # 3. 결합된 피드백 반환
        return {
            "timestamp": datetime.now().isoformat(),
            "full_text": basic_feedback.get("full_text", ""),
            "summary": basic_feedback.get(
                "summary", "컨디션 요약 정보를 분석할 수 없습니다."
            ),
            "mood_analysis": basic_feedback.get(
                "mood_analysis", "감정 상태 정보를 분석할 수 없습니다."
            ),
            "recommendations": text_recommendations,
            "precautions": basic_feedback.get("precautions", []),
            "medical_tips": medical_info.get("tips", []),
            "sources": medical_info.get("sources", []),
        }

    def _generate_basic_feedback(
        self, interactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """기본 피드백 생성"""
        # 상호작용 데이터를 문자열로 변환
        interaction_text = ""
        for i, interaction in enumerate(interactions, 1):
            interaction_text += f"질문 {i}: {interaction['question']}\n"
            interaction_text += f"답변 {i}: {interaction['answer']}\n"
            interaction_text += f"감정: {interaction['emotion']}\n\n"

        system_prompt = """
        당신은 산모의 컨디션을 분석하고 개인화된 피드백을 제공하는 전문 산부인과 의사입니다.
        산모의 대화 전체 맥락을 깊이 이해하고, 산모의 신체적, 정신적 상태를 세심하게 배려하는 따뜻하고 공감적인 피드백을 생성해야 합니다.
        
        제공된 대화 데이터를 분석하여 다음을 포함한 종합적인 피드백을 생성하세요:
        
        1. 전반적인 컨디션 요약 - 산모의 상태를 이전 대화 맥락까지 고려하여 포괄적으로 평가
        2. 감정 상태 분석 - 산모의 감정 변화를 면밀히 파악하고 그 원인과 해결책 제시
        3. 맞춤형 권장사항 (3-5개) - 이전에 언급된 내용을 기억하고 반복 없이 새로운 가치 있는 정보 제공
        4. 주의해야 할 사항 (필요한 경우) - 우려되는 징후가 있을 경우 친절하게 조언
        
        산모가 여러 차례의 대화를 했다면, 이전 대화에서 언급된 내용을 기억하고 연속성을 유지하는 것이 중요합니다.
        매번 같은 조언을 반복하지 말고, 산모의 상황 변화에 맞춘 새로운 통찰력을 제공하세요.
        
        응답은 항상 공감적이고 지지적이며 산모를 존중하는 어조로 작성되어야 합니다.
        심각한 건강 문제가 의심되는 경우에만 의료 전문가 상담을 권장하세요.
        """

        user_prompt = f"다음은 산모와의 대화 내용입니다:\n\n{interaction_text}\n\n이 데이터를 바탕으로 산모의 현재 상태와 필요에 맞는 종합적이고 맞춤형 피드백을 제공해주세요. 이전 대화 내용을 기억하고 대화의 연속성을 유지하면서 새로운 가치 있는 정보를 제공해 주세요."

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            feedback_text = completion.choices[0].message.content

            # 피드백 텍스트를 구조화된 형식으로 변환
            # 여기서는 간단한 텍스트 분석으로 구분
            lines = feedback_text.split("\n")
            summary = ""
            mood_analysis = ""
            recommendations = []
            precautions = []

            current_section = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if "요약" in line or "컨디션" in line and len(line) < 30:
                    current_section = "summary"
                    continue
                elif "감정" in line or "상태" in line and len(line) < 30:
                    current_section = "mood"
                    continue
                elif "권장" in line or "추천" in line and len(line) < 30:
                    current_section = "recommendations"
                    continue
                elif "주의" in line or "주의사항" in line and len(line) < 30:
                    current_section = "precautions"
                    continue

                if current_section == "summary":
                    summary += line + " "
                elif current_section == "mood":
                    mood_analysis += line + " "
                elif current_section == "recommendations" and line.startswith(
                    ("- ", "• ", "· ", "1. ", "2. ", "3. ", "4. ", "5. ")
                ):
                    recommendations.append(line.lstrip("- •·").strip())
                elif current_section == "precautions" and line.startswith(
                    ("- ", "• ", "· ", "1. ", "2. ", "3. ", "4. ", "5. ")
                ):
                    precautions.append(line.lstrip("- •·").strip())

            return {
                "full_text": feedback_text,
                "summary": summary.strip() or "컨디션 요약 정보를 분석할 수 없습니다.",
                "mood_analysis": mood_analysis.strip()
                or "감정 상태 정보를 분석할 수 없습니다.",
                "recommendations": recommendations
                or ["맞춤형 권장사항을 생성할 수 없습니다."],
                "precautions": precautions,
            }

        except Exception as e:
            print(f"피드백 생성 중 오류 발생: {e}")
            return {
                "full_text": "피드백 생성 중 오류가 발생했습니다.",
                "summary": "피드백 생성 실패",
                "mood_analysis": "분석 불가",
                "recommendations": [
                    "시스템 오류가 발생했습니다. 나중에 다시 시도해주세요."
                ],
                "precautions": [],
            }

    def save_feedback(
        self, feedback: Dict[str, Any], session_id: str, output_dir: str = "output"
    ) -> str:
        """
        생성된 피드백을 파일로 저장

        Args:
            feedback: 생성된 피드백 딕셔너리
            session_id: 세션 ID
            output_dir: 출력 디렉토리

        Returns:
            저장된 파일 경로
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        filename = f"{output_dir}/feedback_{session_id}.md"

        with open(filename, "w", encoding="utf-8") as f:
            f.write("# 산모 컨디션 체크 피드백\n\n")
            f.write(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 컨디션 요약\n\n")
            f.write(feedback["summary"] + "\n\n")

            f.write("## 감정 상태 분석\n\n")
            f.write(feedback["mood_analysis"] + "\n\n")

            f.write("## 맞춤형 권장사항\n\n")
            for rec in feedback["recommendations"]:
                f.write(f"- {rec}\n")
            f.write("\n")

            if feedback["precautions"]:
                f.write("## 주의사항\n\n")
                for prec in feedback["precautions"]:
                    f.write(f"- {prec}\n")
                f.write("\n")

            if feedback["medical_tips"]:
                f.write("## 관련 의학 정보\n\n")
                for tip in feedback["medical_tips"]:
                    f.write(f"- {tip}\n")
                f.write("\n")

            if feedback["sources"]:
                f.write("## 참고 자료\n\n")
                for source in feedback["sources"]:
                    f.write(f"- {source}\n")
                f.write("\n")

            f.write("---\n\n")
            f.write(
                "*이 피드백은 자동 생성된 내용으로, 의학적 진단이나 처방을 대체할 수 없습니다.*\n"
            )
            f.write("*건강 관련 우려사항이 있으면 의료 전문가와 상담하세요.*\n")

        return filename

    def _crawl_medical_info(self, keywords: List[str]) -> Dict[str, Any]:
        """
        주어진 키워드를 기반으로 Firecrawl을 사용하여 의료 정보를 크롤링합니다.
        
        Args:
            keywords: 검색할 의료 관련 키워드 리스트
            
        Returns:
            의료 팁과 출처를 포함한 딕셔너리
        """
        if not keywords:
            return {
                "tips": ["검색할 키워드가 제공되지 않았습니다."],
                "sources": []
            }
        
        tips = []
        sources = []
        
        try:
            # 키워드를 조합하여 검색
            search_query = ' '.join(keywords[:3]) + " 건강 정보"  # 상위 3개 키워드만 사용
            
            # Firecrawl 클라이언트 초기화
            firecrawl = FirecrawlApp()
            
            # 검색 URL 설정 (네이버 건강 정보)
            urls = [
                f"https://search.naver.com/search.naver?query={quote(search_query)}&where=view",
                f"https://health.kdca.go.kr/search/search.es?mid=a20509000000&kwd={quote(search_query)}"
            ]
            
            # 각 URL에서 크롤링 시도
            for url in urls:
                print(f"크롤링 URL: {url}")
                
                try:
                    # Firecrawl을 사용하여 페이지 크롤링
                    result = firecrawl.scrape_url(url)
                    
                    if result and result.markdown:
                        # 마크다운 결과에서 정보 추출
                        content = result.markdown
                        
                        # 내용을 문단으로 분리
                        paragraphs = content.split('\n\n')
                        
                        # 의미 있는 문단 추출 (최대 3개)
                        meaningful_paragraphs = []
                        for p in paragraphs:
                            # 길이와 내용 검증
                            p = p.strip()
                            if len(p) > 50 and not p.startswith('#') and not p.startswith('!'):
                                meaningful_paragraphs.append(p)
                            
                            if len(meaningful_paragraphs) >= 3:
                                break
                        
                        # 팁으로 추가
                        for paragraph in meaningful_paragraphs:
                            # 200자로 제한
                            if len(paragraph) > 200:
                                paragraph = paragraph[:197] + "..."
                            tips.append(paragraph)
                        
                        # 출처 추가
                        sources.append(f"출처: {url}")
                        
                        # 충분한 정보를 찾았으면 중단
                        if len(tips) >= 3:
                            break
                
                except Exception as e:
                    print(f"URL {url} 크롤링 중 오류: {e}")
                    continue
            
            # 결과가 없거나 충분하지 않은 경우 대체 정보 제공
            if not tips:
                print("크롤링 결과가 없거나 불충분함, 기본 의료 정보 사용")
                return self._get_default_medical_info()
                
        except Exception as e:
            print(f"의료 정보 크롤링 중 오류 발생: {e}")
            return self._get_default_medical_info()
            
        return {
            "tips": tips if tips else ["관련 의료 정보를 찾지 못했습니다."],
            "sources": sources
        }
        
    def _get_default_medical_info(self) -> Dict[str, Any]:
        """기본 의료 정보를 제공합니다."""
        return {
            "tips": [
                "규칙적인 수면 패턴은 신체 회복과 면역 기능에 중요합니다.",
                "하루 8잔 이상의 물을 마시는 것이 건강 유지에 도움이 됩니다.",
                "가벼운 일상 활동도 신체 건강 유지에 큰 도움이 됩니다.",
                "식사는 단백질, 탄수화물, 건강한 지방이 균형 잡힌 식단으로 구성하세요."
            ],
            "sources": [
                "대한영양학회: https://www.kns.or.kr",
                "국민건강보험공단 건강정보: https://www.nhis.or.kr"
            ]
        }

    def _extract_keywords(self, interactions: List[Dict[str, Any]]) -> List[str]:
        """
        대화 내용에서 의료 관련 키워드를 추출합니다.
        
        Args:
            interactions: 대화 상호작용 리스트
            
        Returns:
            추출된 키워드 리스트
        """
        # 기본 키워드 세트: 항상 검색에 포함될 키워드
        base_keywords = ["건강", "의료"]
        
        # 대화 내용으로부터 텍스트 추출
        all_text = ""
        for interaction in interactions:
            if "question" in interaction:
                all_text += " " + interaction["question"]
            if "answer" in interaction:
                all_text += " " + interaction["answer"]
        
        # 일반적인 건강 관련 키워드들 (확장 가능)
        health_keywords = [
            "건강", "질병", "증상", "치료", "약물", "영양", "운동", "정신건강", "스트레스", "수면",
            "피로", "통증", "두통", "복통", "불면증", "우울", "불안", "식이요법", "다이어트",
            "비만", "당뇨", "고혈압", "심장", "폐", "간", "신장", "위장", "소화", "면역",
            "감기", "알레르기", "피부", "관절", "근육", "뼈", "영양소", "비타민", "미네랄",
            "단백질", "탄수화물", "지방", "콜레스테롤", "혈당", "혈압", "체중", "체력",
            "예방", "진단", "검진", "수술", "재활", "회복", "임신", "출산", "산후조리"
        ]
        
        # 텍스트에서 건강 관련 키워드 찾기
        found_keywords = []
        for keyword in health_keywords:
            if keyword in all_text:
                found_keywords.append(keyword)
        
        # 기본 키워드와 찾은 키워드 결합
        result_keywords = base_keywords + found_keywords
        
        # 중복 제거 및 최대 5개 키워드로 제한
        unique_keywords = list(dict.fromkeys(result_keywords))
        return unique_keywords[:5]


def generate_feedback(conversation_id):
    """대화 세션에 대한 피드백을 생성하고 저장"""
    try:
        from django.db import transaction
        from ..models import ConversationSession, Message, Feedback
        
        # 대화 세션 가져오기
        conversation = ConversationSession.objects.get(id=conversation_id)
        
        # 메시지 목록 가져오기
        messages = Message.objects.filter(session=conversation).order_by('created_at')
        
        # FeedbackGenerator에 전달할 형식으로 변환
        interactions = []
        for msg in messages:
            if msg.question and msg.answer:  # 질문과 답변이 모두 있는 경우만 포함
                interactions.append({
                    'question': msg.question,
                    'answer': msg.answer,
                    'emotion': msg.emotion or 'neutral'
                })
        
        # 피드백 생성 
        generator = FeedbackGenerator()
        print(f"피드백 생성 시작: 대화 ID={conversation_id}, 상호작용 수={len(interactions)}")
        feedback_data = generator.generate_feedback(interactions)
        
        # 의료 정보가 성공적으로 크롤링 되었는지 확인
        medical_tips = feedback_data.get('medical_tips', [])
        if medical_tips and medical_tips[0] != "관련 의료 정보를 찾지 못했습니다.":
            print(f"의료 정보 크롤링 성공: {len(medical_tips)}개의 팁 수집됨")
        else:
            print("의료 정보 크롤링에 실패했거나 정보가 부족합니다.")
        
        # 피드백 저장
        with transaction.atomic():
            feedback = Feedback.objects.create(
                session=conversation,
                summary=feedback_data.get('summary', ''),
                emotional_analysis=feedback_data.get('mood_analysis', ''),
                health_tips='\n'.join([f"• {rec}" for rec in feedback_data.get('recommendations', [])]),
                medical_info={}
            )
            
            # 의료 정보 저장
            medical_tips = feedback_data.get('medical_tips', [])
            feedback.set_tips(medical_tips)
            feedback.set_sources(feedback_data.get('sources', []))
            feedback.save()
            
        print(f"피드백 생성 완료: {conversation_id}")
        return feedback
        
    except Exception as e:
        print(f"피드백 생성 중 오류 발생: {e}")
        return None
