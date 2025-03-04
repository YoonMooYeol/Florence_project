from typing import List, Dict, Literal, Set
import random

# 감정 상태 유형 정의
EmotionType = Literal["positive", "negative", "neutral"]


class DialogueManager:
    """대화 흐름 및 질문 분기 관리 클래스"""

    def __init__(self):
        """대화 관리자 초기화"""
        self.current_step = 0
        self.max_steps = 10  # 10단계로 변경
        self.question_pools = self._initialize_question_pools()
        self.used_topics = set()  # 이미 사용한 주제 추적
        self.current_emotion = "neutral"  # 현재 감정 상태
        self.available_topics = ["physical", "diet", "sleep", "activity"]  # 주제 목록
        self.current_topic = "physical"  # 기본 주제 설정
        self.topic_sequence = ["physical", "diet", "sleep", "activity"]  # 주제 순서 정의

    def _initialize_question_pools(self) -> Dict[int, Dict[EmotionType, List[str]]]:
        """질문 풀 초기화"""
        return {
            # 1단계: 기분/상태 초기 질문
            "mood_initial": {
                "positive": [
                    "오늘 기분이 어떠신가요?",
                    "오늘 하루는 어떤 기분으로 보내고 계신가요?",
                    "지금 컨디션은 어떠신가요?",
                    "오늘 전반적인 기분은 어떠신가요?",
                    "요즘 기분이 어떠신지 말씀해주세요",
                ],
                "negative": [
                    "오늘은 어떤 기분이신가요?",
                    "지금 기분이 어떠신지 말씀해주실 수 있을까요?",
                    "오늘 컨디션은 어떠신가요?",
                    "오늘 몸 상태나 기분이 어떠신가요?",
                    "어떤 기분으로 하루를 보내고 계신가요?",
                ],
                "neutral": [
                    "오늘 하루 어떻게 지내셨나요?",
                    "요즘 기분이 어떠신가요?",
                    "오늘의 컨디션은 어떠신가요?",
                    "지금 기분이나 상태가 어떠신지 말씀해주세요",
                    "오늘 몸 상태는 어떠신가요?",
                ],
            },
            # 2단계: 기분/상태 후속 질문
            "mood_followup": {
                "positive": [
                    "오늘 특별히 기분이 좋으신 이유가 있으신가요?",
                    "기분이 좋으시다니 다행이에요. 어떤 일이 있으셨나요?",
                    "오늘 특별히 기억에 남는 좋은 순간이 있었나요?",
                    "좋은 기분을 유지하기 위해 특별히 하시는 것이 있나요?",
                    "기분이 좋을 때 특별히 하고 싶은 활동이 있으신가요?",
                ],
                "negative": [
                    "오늘 기분이 안 좋으신 이유가 있으신가요?",
                    "어떤 부분이 가장 힘드신가요?",
                    "불편한 점이 있으시다면 좀 더 자세히 말씀해주실 수 있을까요?",
                    "기분을 개선하기 위해 시도해보신 것이 있나요?",
                    "언제부터 이런 기분이 지속되고 있나요?",
                ],
                "neutral": [
                    "오늘 하루 중 특별히 기억에 남는 순간이 있었나요?",
                    "오늘 하루는 어떻게 보내셨나요?",
                    "평소와 비슷한 하루를 보내고 계신가요?",
                    "오늘 특별한 활동을 하셨나요?",
                    "하루 일과가 어떻게 되시나요?",
                ],
            },
            # 주제별 초기 질문
            # 3-1단계: 신체적 상태 초기 질문
            "physical_initial": {
                "positive": [
                    "신체적으로는 어떤 상태이신가요?",
                    "임신 중 신체적으로 편안한 부분이 있으신가요?",
                    "오늘은 몸 상태가 어떠신가요?",
                    "최근 신체적으로 개선된 점이 있으신가요?",
                    "신체적인 변화에 대해 어떻게 느끼고 계신가요?",
                ],
                "negative": [
                    "신체적으로 불편한 점이 있으신가요?",
                    "어떤 신체적 증상이 가장 불편하신가요?",
                    "몸에 통증이 있는 부위가 있으신가요?",
                    "신체적 불편함이 일상생활에 영향을 주나요?",
                    "몸 상태에 변화가 있으신가요?",
                ],
                "neutral": [
                    "최근 신체적인 변화가 있으셨나요?",
                    "임신 중 어떤 신체적 증상을 경험하고 계신가요?",
                    "오늘 신체 컨디션은 어떠신가요?",
                    "평소와 다른 신체적 감각이 있으신가요?",
                    "아기의 움직임은 어떤가요?",
                ],
            },
            # 3-2단계: 식습관과 영양 초기 질문
            "diet_initial": {
                "positive": [
                    "식사는 어떻게 하고 계신가요?",
                    "음식 섭취에 변화가 있으신가요?",
                    "특별히 즐겨 드시는 음식이 있으신가요?",
                    "임신 후 식욕에 어떤 변화가 있으신가요?",
                    "식습관에 대해 말씀해주세요",
                ],
                "negative": [
                    "식사에 어려움이 있으신가요?",
                    "음식과 관련해 불편함을 느끼시나요?",
                    "특별히 먹기 힘든 음식이 있으신가요?",
                    "식사량에 변화가 있으신가요?",
                    "영양 섭취에 어려움이 있으신가요?",
                ],
                "neutral": [
                    "평소 식사 패턴에 대해 말씀해주세요",
                    "오늘 어떤 음식을 드셨나요?",
                    "식사 시간은 규칙적인 편인가요?",
                    "물은 충분히 드시나요?",
                    "식이 습관에 변화가 있으신가요?",
                ],
            },
            # 3-3단계: 수면과 휴식 초기 질문
            "sleep_initial": {
                "positive": [
                    "수면은 어떠신가요?",
                    "충분한 휴식을 취하고 계신가요?",
                    "잠자리에서 편안함을 느끼시나요?",
                    "수면의 질에 만족하시나요?",
                    "휴식 시간은 충분히 가지고 계신가요?",
                ],
                "negative": [
                    "수면에 어려움이 있으신가요?",
                    "잠드는 것이 힘드신가요?",
                    "자주 깨시나요?",
                    "피로감이 지속되시나요?",
                    "수면과 관련된 불편함이 있으신가요?",
                ],
                "neutral": [
                    "평균적으로 몇 시간 정도 주무시나요?",
                    "수면 패턴에 변화가 있으신가요?",
                    "휴식을 취하는 특별한 방법이 있으신가요?",
                    "낮잠은 자시나요?",
                    "수면의 질은 어떠신가요?",
                ],
            },
            # 3-4단계: 활동과 운동 초기 질문
            "activity_initial": {
                "positive": [
                    "신체 활동은 어떻게 하고 계신가요?",
                    "규칙적인 운동을 하고 계시나요?",
                    "산책이나 가벼운 운동을 즐기시나요?",
                    "활동적인 일상을 유지하고 계신가요?",
                    "운동이 컨디션에 도움이 되시나요?",
                ],
                "negative": [
                    "활동하실 때 불편함이 있으신가요?",
                    "운동이나 활동에 제한을 느끼시나요?",
                    "움직일 때 특별히 불편한 부위가 있으신가요?",
                    "활동량이 줄어들어 걱정되시는 부분이 있나요?",
                    "어떤 활동이 가장 힘드신가요?",
                ],
                "neutral": [
                    "평소 활동량은 어느 정도인가요?",
                    "임신 전과 비교해 활동량에 변화가 있으신가요?",
                    "특별히 하고 계신 운동이 있으신가요?",
                    "하루에 어느 정도 걸으시나요?",
                    "일상 활동에 대해 말씀해주세요",
                ],
            },
            # 4-1단계: 신체적 상태 후속 질문
            "physical_followup": {
                "positive": [
                    "신체적으로 편안함을 느끼게 하는 특별한 방법이 있으신가요?",
                    "임신 중 불편함이 줄어든 부분이 있으신가요?",
                    "신체적 컨디션을 관리하기 위해 특별히 하는 일이 있으신가요?",
                    "산전 검진에서 듣는 피드백은 어떤가요?",
                    "최근 신체 변화 중 긍정적인 부분이 있다면 무엇인가요?",
                ],
                "negative": [
                    "언제부터 이런 불편함을 느끼셨나요?",
                    "통증이나 불편함이 일상생활에 어떤 영향을 주고 있나요?",
                    "이런 증상에 대해 의료진과 상담해보셨나요?",
                    "증상을 완화하기 위해 시도해본 방법이 있으신가요?",
                    "가장 심한 불편함은 하루 중 언제 느껴지시나요?",
                ],
                "neutral": [
                    "임신 전과 비교했을 때 가장 큰 신체적 변화는 무엇인가요?",
                    "특정 자세에서 더 편안함을 느끼시나요?",
                    "신체적 변화에 적응하기 위한 나만의 방법이 있으신가요?",
                    "임신 중 신체적 변화에 대해 어떻게 준비하고 계신가요?",
                    "규칙적으로 체크하시는 신체적 지표가 있으신가요? (예: 체중, 혈압 등)",
                ],
            },
            # 4-2단계: 식습관과 영양 후속 질문
            "diet_followup": {
                "positive": [
                    "특별히 선호하는 영양제나 보조식품이 있으신가요?",
                    "임신 후 새롭게 즐기게 된 음식이 있나요?",
                    "식사 계획은 어떻게 세우고 계신가요?",
                    "영양 섭취를 위해 특별히 신경 써서 드시는 부분이 있으신가요?",
                    "식욕 증가가 기분에 어떤 영향을 주나요?",
                ],
                "negative": [
                    "입덧이나 소화 불량이 있으신가요?",
                    "음식 냄새에 민감하신가요?",
                    "식사량 감소로 영양 부족이 걱정되시나요?",
                    "특정 음식에 대한 거부감이 생겼나요?",
                    "식사 관련 불편함에 대해 의사와 상담해보셨나요?",
                ],
                "neutral": [
                    "식이 요법에 대한 조언을 받고 계신가요?",
                    "특별히 신경 써서 드시는 음식이 있으신가요?",
                    "하루 식사 횟수는 어떻게 되시나요?",
                    "간식은 어떤 것을 즐겨 드시나요?",
                    "식사와 관련해 궁금한 점이 있으신가요?",
                ],
            },
            # 4-3단계: 수면과 휴식 후속 질문
            "sleep_followup": {
                "positive": [
                    "편안한 수면을 위해 특별히 하시는 것이 있나요?",
                    "잠자리에 드는 시간과 일어나는 시간이 규칙적인가요?",
                    "좋은 수면의 질을 유지하는 비결이 있으신가요?",
                    "낮잠이 밤 수면에 영향을 주나요?",
                    "수면 환경을 개선하기 위해 특별히 한 일이 있으신가요?",
                ],
                "negative": [
                    "어떤 요인이 수면을 방해한다고 생각하시나요?",
                    "수면 중 불편함을 느끼시는 부분이 있나요?",
                    "불면증이나 과다 수면 등의 문제가 있으신가요?",
                    "휴식이 충분하지 않다고 느끼시는 이유가 있으신가요?",
                    "수면 문제로 의료진과 상담해보셨나요?",
                ],
                "neutral": [
                    "편안한 수면 자세가 있으신가요?",
                    "취침 전 루틴이 있으신가요?",
                    "꿈을 자주 꾸시나요?",
                    "수면의 질을 개선하기 위한 계획이 있으신가요?",
                    "주말과 평일의 수면 패턴에 차이가 있으신가요?",
                ],
            },
            # 4-4단계: 활동과 운동 후속 질문
            "activity_followup": {
                "positive": [
                    "어떤 종류의 운동이 가장 편안하신가요?",
                    "신체 활동 후 기분이 어떠신가요?",
                    "임신 중 추천받은 운동이 있으신가요?",
                    "운동이나 활동이 스트레스 해소에 도움이 되시나요?",
                    "신체 활동을 위한 특별한 계획이 있으신가요?",
                ],
                "negative": [
                    "운동이나 활동을 하기 어려운 이유가 있으신가요?",
                    "어떤 활동이 가장 부담스러우신가요?",
                    "활동 제한으로 인한 스트레스가 있으신가요?",
                    "활동량 감소가 다른 부분에 영향을 주고 있나요?",
                    "안전한 활동에 대한 조언을 받고 계신가요?",
                ],
                "neutral": [
                    "임신 중 안전한 운동에 대해 알아보고 계신가요?",
                    "가사 활동은 어느 정도 하고 계신가요?",
                    "활동량을 유지하기 위한 나만의 방법이 있으신가요?",
                    "활동이나 운동을 함께 하는 파트너가 있으신가요?",
                    "미래에 시도해보고 싶은 활동이 있으신가요?",
                ],
            },
            # 5단계: 미래 계획과 기대에 관한 질문
            "future_plans": {
                "positive": [
                    "앞으로의 계획이 있으신가요?",
                    "출산 준비는 어떻게 진행 중이신가요?",
                    "아기를 맞이할 준비 중 가장 즐거운 부분은 무엇인가요?",
                    "출산 후의 생활에 대한 기대가 있으신가요?",
                    "다가오는 변화에 대해 어떤 기대를 하고 계신가요?",
                ],
                "negative": [
                    "앞으로에 대한 걱정이나 불안이 있으신가요?",
                    "출산 준비 과정에서 어려운 점이 있으신가요?",
                    "출산 후 지원 체계에 대한 걱정이 있으신가요?",
                    "육아에 대한 두려움이 있으신가요?",
                    "미래에 대한 준비가 부족하다고 느끼시나요?",
                ],
                "neutral": [
                    "앞으로의 계획에 대해 말씀해주세요",
                    "출산을 준비하는 과정은 어떠신가요?",
                    "출산 후 도움을 받을 수 있는 분들이 계신가요?",
                    "아기 방이나 필요한 물품은 준비 중이신가요?",
                    "산후 조리에 대한 계획이 있으신가요?",
                ],
            },
        }

    def get_next_question(self, emotion: EmotionType = "neutral") -> str:
        """현재 단계와 감정 상태에 맞는 다음 질문 반환"""
        self.current_emotion = emotion
        next_question = ""

        # 단계별 질문 선택 로직
        if self.current_step == 0:
            # 1단계: 기분/상태 초기 질문
            question_pool = self.question_pools["mood_initial"].get(
                emotion, self.question_pools["mood_initial"]["neutral"]
            )
            next_question = random.choice(question_pool)

        elif self.current_step == 1:
            # 2단계: 기분/상태 후속 질문
            question_pool = self.question_pools["mood_followup"].get(
                emotion, self.question_pools["mood_followup"]["neutral"]
            )
            next_question = random.choice(question_pool)

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
                
            # 질문 풀에서 질문 선택
            question_pool = self.question_pools[topic_key].get(
                emotion, self.question_pools[topic_key]["neutral"]
            )
            next_question = random.choice(question_pool)
            
            # 현재 선택된 주제 저장
            self.current_topic = topic
            self.used_topics.add(topic)

        elif self.current_step == self.max_steps - 1:
            # 마지막 단계: 마무리 질문
            question_pool = self.question_pools["future_plans"].get(
                emotion, self.question_pools["future_plans"]["neutral"]
            )
            next_question = random.choice(question_pool)

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
