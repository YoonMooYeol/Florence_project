from typing import Dict, Literal
from pydantic import BaseModel
from openai import OpenAI
import os

# 감정 상태 유형 정의
EmotionType = Literal["positive", "negative", "neutral"]


class EmotionResponse(BaseModel):
    """감정 분석 응답을 위한 모델"""

    emotion: EmotionType
    confidence: float
    explanation: str


class EmotionAnalyzer:
    """사용자 응답에서 감정 상태를 분석하는 클래스"""

    def __init__(self, client: OpenAI = None):
        """
        감정 분석기 초기화

        Args:
            client: OpenAI 클라이언트. None인 경우 자동으로 생성
        """
        self.client = client if client else OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"  # 기본 모델 설정

    def analyze_emotion(self, text: str) -> Dict:
        """
        사용자 입력 텍스트에서 감정 상태를 분석

        Args:
            text: 감정 분석할 사용자 입력 텍스트

        Returns:
            감정 분석 결과가 포함된 딕셔너리 {'emotion': str, 'confidence': float, 'explanation': str}
        """
        system_prompt = """
        당신은 사용자 텍스트에서 감정을 정확하게 분석하는 시스템입니다.
        특히 임산부/산모의 감정을 분석하는 데 특화되어 있습니다.
        텍스트를 분석하고 감정 상태를 'positive', 'negative', 'neutral' 중 하나로 분류하세요.
        한국어 표현의 미묘한 뉘앙스를 고려하세요. 예를 들어:
        - "좋아"와 같은 표현은 문맥에 따라 긍정적이거나 부정적(비꼬는 표현)일 수 있습니다.
        - 짧은 응답("응", "아니", "모르겠어" 등)은 텍스트만으로 감정을 정확히 판단하기 어려울 수 있습니다.
        
        응답은 감정 유형, 신뢰도(0.0~1.0), 그리고 분석 근거를 포함해야 합니다.
        """

        user_prompt = f"다음 텍스트에서 감정 상태를 분석해주세요: '{text}'"

        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=EmotionResponse,
            )

            return {
                "emotion": completion.choices[0].message.parsed.emotion,
                "confidence": completion.choices[0].message.parsed.confidence,
                "explanation": completion.choices[0].message.parsed.explanation,
            }

        except Exception as e:
            print(f"감정 분석 중 오류 발생: {e}")
            # 오류 발생 시 기본값으로 중립 반환
            return {
                "emotion": "neutral",
                "confidence": 0.5,
                "explanation": "감정 분석 중 오류가 발생하여 기본값을 반환합니다.",
            }

    def analyze_emotion_with_context(
        self, question: str, answer: str, conversation_history=None
    ) -> Dict:
        """
        질문과 답변의 맥락을 고려하여 감정 상태를 더 정확하게 분석

        Args:
            question: 사용자에게 한 질문
            answer: 사용자의 답변
            conversation_history: 이전 대화 내용 목록 (선택 사항)

        Returns:
            맥락을 고려한 감정 분석 결과
        """
        system_prompt = """
        당신은 질문과 답변의 맥락을 고려하여 감정을 정확하게 분석하는 시스템입니다.
        특히 임산부/산모의 대화에서 감정을 분석하는 데 특화되어 있습니다.
        
        대화 맥락을 분석하고 감정 상태를 'positive', 'negative', 'neutral' 중 하나로 분류하세요.
        한국어 표현의 미묘한 뉘앙스와 문화적 맥락을 고려하세요:
        
        1. 짧은 응답("응", "아니", "모르겠어" 등)은 질문의 맥락을 함께 고려해야 합니다.
        2. 비꼬는 표현이나 반어법("조좋아", "완전 좋지" 등)은 실제로는 부정적 감정을 나타낼 수 있습니다.
        3. 감정 변화 패턴을 고려하세요 - 이전 대화에서 감정 상태가 급격히 변한다면 추가 분석이 필요합니다.
        4. 산모 특유의 감정 표현에 주의하세요 - 임신/출산과 관련된 불안, 기대, 두려움 등이 복합적으로 나타날 수 있습니다.
        
        응답은 감정 유형, 신뢰도(0.0~1.0), 그리고 분석 근거를 포함해야 합니다.
        """

        # 기본 대화 맥락 구성
        context = f"질문: {question}\n답변: {answer}\n"

        # 이전 대화 내용이 있으면 추가
        history_text = ""
        if conversation_history:
            history_text = "이전 대화 내용:\n"
            for i, entry in enumerate(
                conversation_history[-3:], 1
            ):  # 최근 3개 대화만 포함
                q = entry.get("question", "")
                a = entry.get("answer", "")
                e = entry.get("emotion", "")
                if q and a:
                    history_text += f"{i}. 질문: {q}\n   답변: {a}\n   감정: {e}\n"

        user_prompt = f"""다음 대화에서 현재 감정 상태를 분석해주세요:

{history_text}
        
현재 대화:
{context}

위 대화에서 답변자의 감정 상태는 어떠한가요?"""

        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=EmotionResponse,
            )

            return {
                "emotion": completion.choices[0].message.parsed.emotion,
                "confidence": completion.choices[0].message.parsed.confidence,
                "explanation": completion.choices[0].message.parsed.explanation,
            }

        except Exception as e:
            print(f"맥락 기반 감정 분석 중 오류 발생: {e}")
            # 오류 발생 시 기본 감정 분석 시도
            return self.analyze_emotion(answer)
