# -------------------------------
# LLM Helper Functions
# -------------------------------

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
import os


def get_system_prompt() -> str:
    """시스템 프롬프트 생성"""
    now = datetime.now().isoformat()
    return f"""당신은 산모를 위한 컨디션 체크 시스템입니다. 오늘 날짜는 {now}입니다.
    공감적이고 지지적인 태도로 답변하며, 산모의 상태를 정확히 이해하기 위해 노력하세요.
    모든 질문과 답변은 한국어로 제공되어야 합니다.
    산모의 감정과 컨디션을 정확히 파악하여 적절한 피드백을 제공하는 것이 목표입니다.
    의학적 조언을 제공할 때는 매우 신중하게 접근하고, 심각한 증상이 의심되는 경우 반드시 의료 전문가 상담을 권장하세요."""


def llm_call(prompt: str, model: str, client) -> str:
    """
    주어진 프롬프트로 LLM을 동기적으로 호출합니다.
    """
    messages = [{"role": "user", "content": prompt}]
    chat_completion = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    print(model, "완료")
    return chat_completion.choices[0].message.content


def json_llm(
    user_prompt: str,
    schema: BaseModel,
    client,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
):
    """
    JSON 모드에서 언어 모델 호출을 실행하고 구조화된 JSON 객체를 반환합니다.
    """
    if model is None:
        model = "gpt-4o-mini"
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        completion = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=schema,
        )

        return completion.choices[0].message.parsed
    except Exception as e:
        print(f"Error in json_llm: {e}")
        return None


def format_feedback_for_display(feedback: Dict[str, Any]) -> str:
    """
    피드백 데이터를 표시용으로 포맷팅

    Args:
        feedback: 피드백 데이터 딕셔너리

    Returns:
        포맷팅된 피드백 문자열
    """
    if not feedback:
        return "피드백 데이터가 없습니다."

    formatted = "# 산모 컨디션 체크 피드백\n\n"

    formatted += "## 컨디션 요약\n\n"
    formatted += feedback.get("summary", "요약 정보 없음") + "\n\n"

    formatted += "## 감정 상태 분석\n\n"
    formatted += feedback.get("mood_analysis", "감정 분석 정보 없음") + "\n\n"

    formatted += "## 맞춤형 권장사항\n\n"
    for rec in feedback.get("recommendations", ["권장사항 없음"]):
        formatted += f"- {rec}\n"
    formatted += "\n"

    if feedback.get("precautions"):
        formatted += "## 주의사항\n\n"
        for prec in feedback["precautions"]:
            formatted += f"- {prec}\n"
        formatted += "\n"

    if feedback.get("medical_tips"):
        formatted += "## 관련 의학 정보\n\n"
        for tip in feedback["medical_tips"]:
            formatted += f"- {tip}\n"
        formatted += "\n"

    if feedback.get("sources"):
        formatted += "## 참고 자료\n\n"
        for source in feedback["sources"]:
            formatted += f"- {source}\n"
        formatted += "\n"

    formatted += "---\n\n"
    formatted += "*이 피드백은 자동 생성된 내용으로, 의학적 진단이나 처방을 대체할 수 없습니다.*\n"
    formatted += "*건강 관련 우려사항이 있으면 의료 전문가와 상담하세요.*\n"

    return formatted


def ensure_dir_exists(directory: str) -> None:
    """
    디렉토리가 존재하는지 확인하고 없으면 생성

    Args:
        directory: 확인할 디렉토리 경로
    """
    if not os.path.exists(directory):
        os.makedirs(directory)


def analyze_emotion(text):
    """
    사용자 메시지의 감정을 분석하는 함수
    
    Args:
        text (str): 분석할 텍스트
        
    Returns:
        str: 감정 유형 ("positive", "negative", "neutral" 중 하나)
    """
    # 간단한 감정 분석 로직 (실제로는 더 복잡한 감정 분석 모델을 사용할 수 있음)
    positive_words = [
        "좋", "행복", "기쁘", "즐겁", "편안", "만족", "감사", "사랑", "희망", "설레", 
        "웃", "신나", "활기", "기대", "긍정", "좋아", "최고", "멋지", "아름다운", "훌륭한"
    ]
    
    negative_words = [
        "나쁘", "슬프", "우울", "불안", "걱정", "화나", "짜증", "피곤", "힘들", "아프", 
        "불편", "고통", "싫", "실망", "후회", "두렵", "무섭", "괴롭", "외롭", "불만"
    ]
    
    # 긍정/부정 단어 카운트
    positive_count = sum(1 for word in positive_words if word in text)
    negative_count = sum(1 for word in negative_words if word in text)
    
    # 감정 판단
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    else:
        return "neutral"
