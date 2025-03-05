from typing import List, Dict, Literal, Set, Optional
import random
import os
from openai import OpenAI
from pydantic import BaseModel

# 감정 상태 유형 정의
EmotionType = Literal["positive", "negative", "neutral"]

# 질문 응답 스키마 정의
class QuestionResponse(BaseModel):
    """LLM에서 생성된 질문 응답 스키마"""
    questions: List[str]

class DialogueManager:
    """대화 흐름 및 질문 분기 관리 클래스"""

    def __init__(self, client: Optional[OpenAI] = None):
        """대화 관리자 초기화"""
        self.current_step = 0
        self.max_steps = 10  # 10단계로 변경
        self.used_topics = set()  # 이미 사용한 주제 추적
        self.current_emotion = "neutral"  # 현재 감정 상태
        self.available_topics = ["physical", "diet", "sleep", "activity"]  # 주제 목록
        self.current_topic = "physical"  # 기본 주제 설정
        self.topic_sequence = ["physical", "diet", "sleep", "activity"]  # 주제 순서 정의
        
        # LLM 클라이언트 초기화
        self.client = client if client else OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"  # 빠른 모델 선택
        
        # 질문 풀 초기화 - 미리 생성된 질문을 사용하지 않고 필요할 때마다 생성
        self.question_categories = self._initialize_question_categories()

    def _initialize_question_categories(self) -> Dict[str, Dict[str, str]]:
        """
        질문 카테고리와 지시사항 초기화
        하드코딩된 질문 대신 LLM 지시사항만 정의
        """
        return {
            # 1단계: 기분/상태 초기 질문
            "mood_initial": {
                "description": "산모의 전반적인 기분과 컨디션을 물어보는 첫 번째 질문",
                "positive": "산모가 긍정적인 상태일 때 물어볼 수 있는 기분/컨디션 관련 질문",
                "negative": "산모가 부정적인 상태일 때 공감하며 물어볼 수 있는 기분/컨디션 관련 질문",
                "neutral": "산모의 현재 기분이나 컨디션을 물어보는 중립적인 질문"
            },
            # 2단계: 기분/상태 후속 질문
            "mood_followup": {
                "description": "첫 번째 질문에 대한 답변을 바탕으로 더 자세히 기분을 탐색하는 후속 질문",
                "positive": "긍정적인 감정에 대해 더 자세히 물어보는 후속 질문",
                "negative": "부정적인 감정이나 어려움에 대해 공감하며 더 자세히 물어보는 질문",
                "neutral": "중립적인 상태에서 하루 일과나 특별한 경험에 대해 물어보는 질문"
            },
            # 주제별 초기 질문
            # 3-1단계: 신체적 상태 초기 질문
            "physical_initial": {
                "description": "산모의 신체적 상태와 변화에 대해 물어보는 질문",
                "positive": "신체적으로 편안하거나 긍정적 변화를 경험 중인 산모에게 물어볼 질문",
                "negative": "신체적 불편함이나 통증을 느끼는 산모에게 공감하며 물어볼 질문",
                "neutral": "임신 중 신체적 변화나 컨디션에 대해 물어보는 중립적인 질문"
            },
            # 3-2단계: 식습관과 영양 초기 질문
            "diet_initial": {
                "description": "산모의 식습관과 영양 상태에 대해 물어보는 질문",
                "positive": "식사와 영양에 대해 긍정적인 경험을 하는 산모에게 물어볼 질문",
                "negative": "식사나 음식 섭취에 어려움을 겪는 산모에게 공감하며 물어볼 질문",
                "neutral": "평소 식습관이나 식사 패턴에 대해 물어보는 중립적인 질문"
            },
            # 3-3단계: 수면과 휴식 초기 질문
            "sleep_initial": {
                "description": "산모의 수면과 휴식에 관련된 질문",
                "positive": "수면과 휴식이 충분한 산모에게 물어볼 질문",
                "negative": "수면 부족이나 불면증을 겪는 산모에게 공감하며 물어볼 질문",
                "neutral": "평소 수면 패턴이나 휴식에 대해 물어보는 중립적인 질문"
            },
            # 3-4단계: 활동과 운동 초기 질문
            "activity_initial": {
                "description": "산모의 신체 활동과 운동에 관련된 질문",
                "positive": "활동적인 일상을 유지하는 산모에게 물어볼 질문",
                "negative": "활동에 제한을 느끼거나 불편함을 겪는 산모에게 공감하며 물어볼 질문",
                "neutral": "평소 활동량이나 운동 습관에 대해 물어보는 중립적인 질문"
            },
            # 4-1단계: 신체적 상태 후속 질문
            "physical_followup": {
                "description": "신체적 상태에 대한 첫 질문 이후 더 깊이 탐색하는 후속 질문",
                "positive": "신체적 편안함이나 긍정적 측면에 대해 더 자세히 물어보는 질문",
                "negative": "신체적 불편함의 세부 사항이나 영향에 대해 공감하며 물어보는 질문",
                "neutral": "신체 변화에 대한 적응 방법이나 경험에 대해 더 자세히 물어보는 질문"
            },
            # 4-2단계: 식습관과 영양 후속 질문
            "diet_followup": {
                "description": "식습관과 영양에 대한 첫 질문 이후 더 깊이 탐색하는 후속 질문",
                "positive": "영양 섭취와 식사 계획에 대해 더 자세히 물어보는 긍정적인 질문",
                "negative": "식사 관련 어려움의 원인이나 해결 방법에 대해 공감하며 물어보는 질문",
                "neutral": "식이 요법이나 영양 보충에 대한 구체적인 접근 방식에 대해 물어보는 질문"
            },
            # 4-3단계: 수면과 휴식 후속 질문
            "sleep_followup": {
                "description": "수면과 휴식에 대한 첫 질문 이후 더 깊이 탐색하는 후속 질문",
                "positive": "좋은 수면을 유지하는 방법이나 휴식의 질에 대해 더 자세히 물어보는 질문",
                "negative": "수면 문제의 원인이나 영향에 대해 공감하며 물어보는 질문",
                "neutral": "수면 환경이나 취침 전 루틴에 대해 더 자세히 물어보는 질문"
            },
            # 4-4단계: 활동과 운동 후속 질문
            "activity_followup": {
                "description": "활동과 운동에 대한 첫 질문 이후 더 깊이 탐색하는 후속 질문",
                "positive": "운동의 효과나 선호하는 활동에 대해 더 자세히 물어보는 질문",
                "negative": "활동 제한의 영향이나 대체 방법에 대해 공감하며 물어보는 질문",
                "neutral": "안전한 운동 방법이나 활동 계획에 대해 더 자세히 물어보는 질문"
            },
            # 5단계: 미래 계획과 기대에 관한 질문
            "future_plans": {
                "description": "출산 준비와 미래 계획에 관한 질문",
                "positive": "앞으로의 계획이나 기대에 대해 긍정적으로 물어보는 질문",
                "negative": "미래에 대한 걱정이나 불안에 공감하며 물어보는 질문",
                "neutral": "출산 준비나 앞으로의 계획에 대해 중립적으로 물어보는 질문"
            },
        }

    def _generate_questions(self, category: str, emotion: EmotionType) -> List[str]:
        """
        LLM을 사용하여 해당 카테고리와 감정 상태에 맞는 질문 생성
        
        Args:
            category (str): 질문 카테고리
            emotion (EmotionType): 감정 상태
            
        Returns:
            List[str]: 생성된 질문 목록
        """
        try:
            # 카테고리 정보 가져오기
            category_info = self.question_categories.get(category, {})
            description = category_info.get("description", "산모에게 물어볼 질문")
            emotion_guidance = category_info.get(emotion, category_info.get("neutral", "중립적인 질문"))
            
            # 시스템 프롬프트 생성
            system_prompt = """
            당신은 산모를 위한 컨디션 체크 시스템의 질문 생성 모듈입니다.
            주어진 카테고리와 감정 상태에 맞는 양질의 질문을 5개 생성해주세요.
            질문은 공감적이고 지지적인 어조로 작성되어야 하며, 산모의 건강과 감정을 존중해야 합니다.
            모든 질문은 한국어로 제공되어야 합니다.
            """
            
            # 사용자 프롬프트 생성
            user_prompt = f"""
            다음 카테고리와 감정 상태에 맞는 산모 대상 질문 5개를 생성해주세요:
            
            카테고리: {category} - {description}
            감정 상태: {emotion} - {emotion_guidance}
            
            질문은 친절하고 공감적인 어조로, 자연스러운 대화 형식으로 작성해주세요.
            한 문장으로 된 간결한 질문으로 작성해주세요.
            """
            
            # LLM 호출
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=QuestionResponse,
            )
            
            # 결과 반환
            return completion.choices[0].message.parsed.questions
            
        except Exception as e:
            print(f"질문 생성 중 오류 발생: {e}")
            # 오류 발생 시 기본 질문 반환
            return [
                f"{category.replace('_', ' ').title()}에 대해 어떻게 생각하시나요?",
                f"{category.replace('_', ' ').title()}와 관련하여 어떤 경험을 하고 계신가요?",
                f"최근 {category.replace('_', ' ')}에 변화가 있으셨나요?",
                f"{category.replace('_', ' ')}에 대해 더 이야기해주실 수 있을까요?",
                f"{category.replace('_', ' ')}와 관련하여 특별히 신경 쓰시는 부분이 있나요?"
            ]

    def get_next_question(self, emotion: EmotionType = "neutral") -> str:
        """현재 단계와 감정 상태에 맞는 다음 질문 반환"""
        self.current_emotion = emotion
        next_question = ""

        # 단계별 질문 선택 로직
        if self.current_step == 0:
            # 1단계: 기분/상태 초기 질문
            questions = self._generate_questions("mood_initial", emotion)
            next_question = random.choice(questions)

        elif self.current_step == 1:
            # 2단계: 기분/상태 후속 질문
            questions = self._generate_questions("mood_followup", emotion)
            next_question = random.choice(questions)

        elif self.current_step >= 2 and self.current_step < self.max_steps - 1:
            # 3단계부터 마지막 단계 전까지: 주제 기반 질문
            # 현재 단계에 맞는 주제 선택
            topic_index = (self.current_step - 2) % len(self.topic_sequence)
            topic = self.topic_sequence[topic_index]
            
            # 짝수 단계는 초기 질문, 홀수 단계는 후속 질문
            if (self.current_step % 2) == 0:  # 짝수 단계 (0부터 시작하므로 2, 4, 6, 8)
                topic_key = f"{topic}_initial"
            else:  # 홀수 단계 (3, 5, 7, 9)
                topic_key = f"{topic}_followup"
                
            # LLM으로 질문 생성
            questions = self._generate_questions(topic_key, emotion)
            next_question = random.choice(questions)
            
            # 현재 선택된 주제 저장
            self.current_topic = topic
            self.used_topics.add(topic)

        elif self.current_step == self.max_steps - 1:
            # 마지막 단계: 마무리 질문
            questions = self._generate_questions("future_plans", emotion)
            next_question = random.choice(questions)

        # 다음 단계로 이동
        self.current_step += 1
        
        return next_question

    def reset(self):
        """대화 상태 초기화"""
        self.current_step = 0
        self.used_topics = set()
        self.current_emotion = "neutral"

    def is_conversation_complete(self) -> bool:
        """대화 완료 여부 확인"""
        return self.current_step >= self.max_steps
