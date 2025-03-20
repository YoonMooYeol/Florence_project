import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel

from agents import Agent, Runner, WebSearchTool, FileSearchTool, trace, handoff, input_guardrail, output_guardrail, GuardrailFunctionOutput
from agents import RunHooks, RunContextWrapper, Usage, Tool
from django.conf import settings
from django.db import models
from django.utils import timezone
from .models import LLMConversation, ChatManager
import asyncio
from asgiref.sync import sync_to_async

# 환경 변수 로드
load_dotenv()

model_name = os.getenv("LLM_MODEL") or "gpt-4o-mini"
openai_api_key = os.getenv("OPENAI_API_KEY")
vector_store_id = os.getenv("VECTOR_STORE_ID")  # 벡터 스토어 ID

# 라이프사이클 추적을 위한 훅 클래스
class PregnancyAgentHooks(RunHooks):
    def __init__(self):
        self.event_counter = 0
        self.agent_responses = {}
        self.tool_results = {}
        self.handoffs = []

    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        self.event_counter += 1
        self.agent_responses[agent.name] = {"start_time": timezone.now(), "response": ""}

    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        self.event_counter += 1
        if agent.name in self.agent_responses:
            self.agent_responses[agent.name]["end_time"] = timezone.now()
            self.agent_responses[agent.name]["response"] = str(output)

    async def on_handoff(self, context: RunContextWrapper, from_agent: Agent, to_agent: Agent) -> None:
        self.event_counter += 1
        self.handoffs.append({
            "from": from_agent.name,
            "to": to_agent.name,
            "time": timezone.now()
        })
        
    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        self.event_counter += 1
        tool_key = f"{agent.name}_{tool.name}_{self.event_counter}"
        self.tool_results[tool_key] = {"start_time": timezone.now(), "result": None}
        
    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str) -> None:
        self.event_counter += 1
        tool_key = f"{agent.name}_{tool.name}_{self.event_counter-1}"
        if tool_key in self.tool_results:
            self.tool_results[tool_key]["end_time"] = timezone.now()
            self.tool_results[tool_key]["result"] = result

    def get_metrics(self) -> Dict[str, Any]:
        """에이전트 실행 메트릭 반환"""
        return {
            "event_count": self.event_counter,
            "agent_responses": self.agent_responses,
            "tool_results": self.tool_results,
            "handoffs": self.handoffs
        }

# 데이터 검증을 위한 Pydantic 모델들
class DataValidationResult(BaseModel):
    is_accurate: bool
    confidence_score: float  # 0.0 ~ 1.0
    reason: str
    corrected_information: Optional[str] = None

class QueryClassification(BaseModel):
    """질문 분류 결과"""
    category: str  # 'medical', 'policy', 'nutrition', 'exercise', 'emotional', 'general'
    confidence: float  # 0.0 ~ 1.0
    needs_verification: bool  # 정보 검증이 필요한지 여부

# Django ORM과 통합된 컨텍스트 모델
class PregnancyContext:
    """임신 관련 정보를 저장하는 컨텍스트 클래스"""
    
    def __init__(self, user_id=None, thread_id=None):
        self.pregnancy_week: Optional[int] = None
        self.user_info: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, Any]] = []
        self.conversation_summary: str = ""
        self.verification_results: List[DataValidationResult] = []
        self.user_id = user_id
        self.thread_id = thread_id
        
        # 유저 ID가 제공된 경우 DB에서 관련 정보 로드 -> 여기서 DB를 바로 로드하지 않음!
        # if user_id:
        #     self._load_user_data()
    
    async def load_user_data_async(self):
        """
        ORM을 비동기 문맥에서 호출할 수 있도록 sync_to_async 사용.
        실제 DB에서 사용자 및 임신 정보, 대화 등을 로드.
        """
        from accounts.models import User, Pregnancy

        # 1) user 불러오기 (동기 ORM -> sync_to_async)
        try:
            user = await sync_to_async(User.objects.get)(user_id=self.user_id)
        except User.DoesNotExist:
            print(f"사용자 데이터 로드 중 오류: user_id={self.user_id} 해당 사용자가 없습니다.")
            return

        self.user_info = {
            "name": user.name,
            "is_pregnant": user.is_pregnant,
            "email": user.email,
        }

        # 2) 임신 정보 불러오기
        pregnancy = await sync_to_async(Pregnancy.objects.filter(user=user).order_by('-created_at').first)()
        if pregnancy:
            self.pregnancy_week = pregnancy.current_week
            self.user_info["pregnancy_id"] = str(pregnancy.pregnancy_id)
            self.user_info["due_date"] = pregnancy.due_date.isoformat() if pregnancy.due_date else None
            self.user_info["baby_name"] = pregnancy.baby_name

        # 3) 대화 로드 (최근 5개)
        from .models import ChatManager, LLMConversation

        if self.thread_id:
            # 특정 채팅방
            chat_room = await sync_to_async(ChatManager.objects.filter(chat_id=self.thread_id).first)()
            if chat_room:
                conversations = await sync_to_async(
                    lambda: list(LLMConversation.objects.filter(chat_room=chat_room).order_by('-created_at')[:5])
                )()
            else:
                conversations = []
        else:
            # 사용자의 전체 최근 대화
            conversations = await sync_to_async(
                lambda: list(LLMConversation.objects.filter(user=user).order_by('-created_at')[:5])
            )()

        # 4) self.conversation_history 채우기
        for conv in reversed(conversations):
            self.conversation_history.append({
                "user": conv.query,
                "assistant": conv.response,
                "created_at": conv.created_at.isoformat()
            })

        # 5) 대화 요약
        self._update_conversation_summary()
    
    def update_pregnancy_week(self, week: int):
        """임신 주차 정보 업데이트"""
        self.pregnancy_week = week
        
    def add_user_info(self, key: str, value: Any):
        """사용자 정보 추가(태명, 이름, 나이 등등)"""
        self.user_info[key] = value
    
    def add_conversation(self, user_input: str, assistant_output: str):
        """대화 추가 및 컨텍스트 요약 업데이트"""
        self.conversation_history.append({
            "user": user_input,
            "assistant": assistant_output,
            "created_at": timezone.now().isoformat()
        })
        
        # 대화 요약 업데이트
        self._update_conversation_summary()
    
    def _update_conversation_summary(self):
        """대화 내역 요약 업데이트"""
        # 최근 3개 대화만 유지
        recent_conversations = self.conversation_history[-3:] if len(self.conversation_history) > 3 else self.conversation_history
        
        summary = "이전 대화 내용:\n"
        for i, conv in enumerate(recent_conversations):
            summary += f"사용자: {conv['user']}\n"
            summary += f"어시스턴트: {conv['assistant']}\n\n"
        
        self.conversation_summary = summary
    
    def add_verification_result(self, result: DataValidationResult):
        """정보 검증 결과 추가"""
        self.verification_results.append(result)
    
    async def save_to_db_async(self, user_input: str, assistant_output: str,
                               source_documents=None, using_rag=False):
        """
        대화 내용을 DB에 저장 (비동기 -> sync_to_async)
        """
        from accounts.models import User, Pregnancy
        from .models import ChatManager, LLMConversation

        if not self.user_id:
            return None

        try:
            user = await sync_to_async(User.objects.get)(user_id=self.user_id)
        except User.DoesNotExist:
            print(f"대화 저장 중 오류: user_id={self.user_id} 해당 사용자가 없습니다.")
            return None

        # 채팅방 관련 처리
        chat_room = None
        if self.thread_id:
            chat_room = await sync_to_async(ChatManager.objects.filter(chat_id=self.thread_id).first)()
            if not chat_room:
                # 없으면 생성
                pregnancy = await sync_to_async(
                    lambda: Pregnancy.objects.filter(user=user).order_by('-created_at').first()
                )()
                chat_room = await sync_to_async(ChatManager.objects.create)(
                    user=user, pregnancy=pregnancy, is_active=True
                )

        # 대화 저장
        conversation = await sync_to_async(LLMConversation.objects.create)(
            user=user,
            chat_room=chat_room,
            query=user_input,
            response=assistant_output,
            user_info=self.user_info,
            source_documents=source_documents or [],
            using_rag=using_rag
        )
        return conversation
    
    def save_to_db(self, user_input: str, assistant_output: str,
                   source_documents=None, using_rag=False):
        """
        (새로 추가)
        동기 ORM으로 DB에 대화 저장.
        동기 뷰 내부에서 편하게 호출하기 위함.
        """
        from accounts.models import User, Pregnancy
        from .models import ChatManager, LLMConversation

        if not self.user_id:
            return None

        try:
            user = User.objects.get(user_id=self.user_id)  # 동기 ORM
        except User.DoesNotExist:
            print(f"대화 저장 중 오류: user_id={self.user_id} 해당 사용자가 없습니다.")
            return None

        # 채팅방 관련 처리
        chat_room = None
        if self.thread_id:
            chat_room = ChatManager.objects.filter(chat_id=self.thread_id).first()
            if not chat_room:
                # 없으면 생성
                pregnancy = Pregnancy.objects.filter(user=user).order_by('-created_at').first()
                chat_room = ChatManager.objects.create(
                    user=user,
                    pregnancy=pregnancy,
                    is_active=True
                )

        # 대화 저장
        conversation = LLMConversation.objects.create(
            user=user,
            chat_room=chat_room,
            query=user_input,
            response=assistant_output,
            user_info=self.user_info,
            source_documents=source_documents or [],
            using_rag=using_rag
        )
        return conversation

# 가드레일 정의
@input_guardrail
def check_appropriate_content(context, agent, input):
    """부적절한 내용이 있는지 확인하는 가드레일"""
    inappropriate_keywords = ["술", "담배", "약물", "다이어트", "살 빼기"]
    
    if isinstance(input, str):
        for keyword in inappropriate_keywords:
            if keyword in input:
                return GuardrailFunctionOutput(
                    output_info=f"부적절한 키워드 '{keyword}'가 포함되어 있습니다",
                    tripwire_triggered=True
                )
    
    return GuardrailFunctionOutput(
        output_info="입력이 적절합니다",
        tripwire_triggered=False
    )

@output_guardrail
def verify_medical_advice(context, agent, output):
    """의학적 조언이 명확한 한계를 가지고 있는지 확인하는 가드레일"""
    disclaimer_keywords = ["의사와 상담", "의료 전문가", "개인차가 있을 수 있습니다"]
    
    has_disclaimer = any(keyword in output for keyword in disclaimer_keywords)
    
    if not has_disclaimer and "medical_agent" in agent.name:
        # 의료 조언에 면책 조항이 없는 경우
        return GuardrailFunctionOutput(
            output_info="의학적 조언에 면책 조항이 없습니다",
            tripwire_triggered=True
        )
    
    return GuardrailFunctionOutput(
        output_info="출력이 적절합니다",
        tripwire_triggered=False
    )

# 컨텍스트를 활용한 동적 지시사항 생성 함수
def create_agent_instructions(context: PregnancyContext, base_instructions: str) -> str:
    """컨텍스트 정보를 활용하여 동적으로 지시사항 생성"""
    instructions = base_instructions
    
    # 사용자 정보 추가
    if context.user_info:
        user_info_str = "사용자 정보:\n"
        for key, value in context.user_info.items():
            user_info_str += f"- {key}: {value}\n"
        instructions += f"\n\n{user_info_str}"
    
    # 임신 주차 정보 추가
    if context.pregnancy_week:
        instructions += f"\n\n현재 임신 주차: {context.pregnancy_week}주차"
    
    # 대화 기록이 있다면 추가
    if context.conversation_history:
        instructions += f"\n\n{context.conversation_summary}"
    
    return instructions

# 질문 분류 에이전트 지시사항
query_classifier_instructions = """
당신은 사용자 질문을 분석하고 적절한 카테고리로 분류하는 전문가입니다.
사용자의 질문을 다음 카테고리 중 하나로 분류하세요:
1. medical: 의학적 정보, 태아 발달, 건강 문제, 증상 등에 관한 질문
2. policy: 정부 지원 정책, 법적 혜택, 지원금 등에 관한 질문
3. nutrition: 영양, 식단, 음식 추천 등에 관한 질문
4. exercise: 임신 중 운동, 신체 활동 등에 관한 질문
5. emotional: 감정적 지원, 스트레스, 불안, 심리 상태 등에 관한 질문
6. general: 위 카테고리에 속하지 않는 일반적인 질문

또한 응답에 대한 검증이 필요한지 판단하세요. 의학 정보, 정책 정보, 영양 정보 등 
사실에 기반한 중요한 정보를 제공해야 하는 경우에는 검증이 필요합니다.

주어진 질문에 가장 적합한 카테고리와 검증 필요 여부를 결정하세요.
"""

# 서브에이전트 기본 지시사항
general_agent_base_instructions = """
당신은 일반적인 대화를 제공하는 도우미입니다.
항상 친절한 말로 답변하세요.
의학적인 질문이나 정부 지원 정책에 관한 구체적인 질문은 다른 전문 에이전트에게 넘기세요.
모든 답변은 한국어로 제공하세요.
"""

medical_agent_base_instructions = """
당신은 임신 주차별 의학 정보를 제공하는 전문가입니다.
사용자의 임신 주차에 맞는 정확한 의학 정보를 제공하세요.
검색이나 데이터를 가져와야할때는 사용자에게 "잠시만요. 정확한 정보전달을 위해 검색을 진행하겠습니다."라고 알려준 후 검색을 진행하세요.
포함되어야 할 정보는 태아발달, 추가 칼로리, 운동, 영양제, 주차별 받아야할 병원진료 등등을 제공하세요. 제공된 정보는 또 제공될 필요는 없지만 필요하다면 제공하세요.
항상 "이 정보는 일반적인 안내이며, 구체적인 의료 조언은 의사와 상담하세요"라는 면책 조항을 포함하세요.
모든 답변은 한국어로 제공하세요.
FileSearchTool에서 가져온 임신 주차별 정보를 활용하세요.
"""

data_verification_agent_base_instructions = """
당신은 임신과 출산 관련 의학 정보의 정확성을 검증하는 전문가입니다.
제공된 정보가 최신 의학 지식에 부합하는지, 과장되거나 잘못된 정보는 없는지 평가하세요.
신뢰할 수 있는 의학 지식을 바탕으로 정보의 정확성을 0.0부터 1.0 사이의 점수로 평가하세요.
정확하지 않은 정보가 있다면 해당 부분을 지적하고 수정된 정보를 제공하세요.

모든 평가는 객관적이고 과학적인 근거에 기반해야 합니다.
"""

policy_agent_base_instructions = """
임산부에게 정부에서 지원하는 정보과 URL을 제공하는 전문가입니다.
검색이나 데이터를 가져와야할때는 사용자에게 "잠시만요. 정확한 정보전달을 위해 검색을 진행하겠습니다."라고 알려준 후 검색을 진행하세요.
맘편한 임신 원스톱 서비스같은 정보를 제공하세요. 그리고 더 많은 정보를 웹검색을 통해 제공하세요. 꼭 지원할수있는 url과 연락처를 제공하세요.
"""

nutrition_agent_base_instructions = """
당신은 임신 주차별 영양 및 식단 정보를 제공하는 전문가입니다.
검색이나 데이터를 가져와야할때는 사용자에게 "잠시만요. 정확한 정보전달을 위해 검색을 진행하겠습니다."라고 알려준 후 검색을 진행하세요.
임신 주차에 따라 필요한 영양소, 권장 식품, 주의해야 할 식품 등에 대한 정보를 제공하세요.
모든 답변은 한국어로 제공하세요.
FileSearchTool에서 가져온 임신 주차별 영양 정보를 활용하세요.
"""

exercise_agent_base_instructions = """
당신은 임신 중 안전한 운동 정보를 제공하는 전문가입니다.
검색이나 데이터를 가져와야할때는 사용자에게 "잠시만요. 정확한 정보전달을 위해 검색을 진행하겠습니다."라고 알려준 후 검색을 진행하세요.
임신 주차에 따른 적절한 운동 유형, 강도, 주의사항 등을 안내하세요.
간단한 스트레칭이나 요가 동작도 설명할 수 있습니다.
모든 답변은 한국어로 제공하세요.
FileSearchTool에서 가져온 임신 주차별 운동 정보를 활용하세요.
"""

emotional_agent_base_instructions = """
당신은 임신 중 감정 변화와 심리적 건강을 지원하는 웹검색 전문가입니다. 현재 이루어진 모든 대화를 분석해서 사용자에게 조언하세요.
검색이나 데이터를 가져와야할때는 사용자에게 "잠시만요. 정확한 정보전달을 위해 검색을 진행하겠습니다."라고 알려준 후 검색을 진행하세요.
또는 임신 중 흔히 겪는 감정 변화, 스트레스 관리법, 심리적 안정을 위한 조언을 웹검색을 통해 제공하세요.
공감하는 태도로 따뜻한 지원을 제공하되, 전문적인 심리 상담이 필요한 경우는 전문가의 연락처를 권유하세요.
모든 답변은 한국어로 제공하세요.
FileSearchTool에서 가져온 임신 주차별 감정 정보를 활용하세요.
"""

# 메인 에이전트 지시사항 수정
main_agent_base_instructions = """
당신은 임신과 출산에 관한 정보를 제공하는 산모 도우미입니다.
사용자의 질문은 이미 분류가 완료되었으며, 당신은 적절한 전문 에이전트에게 연결만 하면 됩니다.

다음은 각 에이전트의 전문 분야입니다:
1. general_agent: 임신과 출산에 관한 일반적인 정보
2. medical_agent: 임신 주차별 의학 정보 
3. policy_agent: 정부 지원 정책 정보
4. nutrition_agent: 임신 중 영양 및 식단 정보
5. exercise_agent: 임신 중 안전한 운동 정보
6. emotional_support_agent: 임신 중 감정 변화와 심리적 건강 지원

에이전트에게 질문을 전달할 때는 다음과 같은 형식의 도구를 사용하세요:
- transfer_to_general_agent: 일반 정보를 요청할 때
- transfer_to_medical_agent: 의학 정보를 요청할 때
- transfer_to_policy_agent: 정책 정보를 요청할 때
- transfer_to_nutrition_agent: 영양 정보를 요청할 때
- transfer_to_exercise_agent: 운동 정보를 요청할 때
- transfer_to_emotional_support_agent: 감정 지원을 요청할 때

사용자의 질문은 '{query_type}' 카테고리로 분류되었으므로, 즉시 해당 전문 에이전트에게 핸드오프하세요.
모든 답변은 한국어로 제공하세요.
"""

class OpenAIAgentService:
    """OpenAI 에이전트 서비스 클래스"""
    
    def __init__(self):
        """서비스 초기화"""
        self.model_name = model_name
        self.openai_api_key = openai_api_key
        self.vector_store_id = vector_store_id
    
    # 질문 분류 에이전트 정의
    def get_query_classifier_agent(self) -> Agent:
        return Agent(
            name="query_classifier_agent",
            model=self.model_name,
            instructions=query_classifier_instructions,
            output_type=QueryClassification
        )

    # 데이터 검증 에이전트 정의
    def get_data_verification_agent(self, context: PregnancyContext) -> Agent:
        return Agent(
            name="data_verification_agent",
            model=self.model_name,
            instructions=create_agent_instructions(context, data_verification_agent_base_instructions),
            output_type=DataValidationResult
        )

    # 서브에이전트 정의 
    def get_general_agent(self, context: PregnancyContext) -> Agent:
        return Agent(
            name="general_agent",
            model=self.model_name,
            instructions=create_agent_instructions(context, general_agent_base_instructions),
            handoff_description="일반적인 대화를 제공합니다.",
            input_guardrails=[check_appropriate_content],
        )

    def get_medical_agent(self, context: PregnancyContext) -> Agent:
        return Agent(
            name="medical_agent",
            model=self.model_name,
            instructions=create_agent_instructions(context, medical_agent_base_instructions),
            handoff_description="임신 주차별 의학 정보를 제공합니다.",
            input_guardrails=[check_appropriate_content],
            output_guardrails=[verify_medical_advice],
            tools=[
                WebSearchTool(),
                FileSearchTool(
                    max_num_results=5,
                    vector_store_ids=[self.vector_store_id],
                    include_search_results=True,
                )
            ],
        )

    def get_policy_agent(self, context: PregnancyContext) -> Agent:
        return Agent(
            name="policy_agent",
            model=self.model_name,
            instructions=create_agent_instructions(context, policy_agent_base_instructions),
            handoff_description="임신과 출산 관련 정부 지원 정책 정보와 연락처를 제공합니다.",
            tools=[WebSearchTool(user_location={"type": "approximate", "city": "South Korea"})],
            input_guardrails=[check_appropriate_content],
        )

    def get_nutrition_agent(self, context: PregnancyContext) -> Agent:
        return Agent(
            name="nutrition_agent",
            model=self.model_name,
            instructions=create_agent_instructions(context, nutrition_agent_base_instructions),
            handoff_description="임신 주차별 영양 및 식단 정보를 제공합니다.",
            input_guardrails=[check_appropriate_content],
            tools=[
                WebSearchTool(user_location={"type": "approximate", "city": "South Korea"}),
                FileSearchTool(
                    max_num_results=5,
                    vector_store_ids=[self.vector_store_id],
                    include_search_results=True,
                )
            ],
        )

    def get_exercise_agent(self, context: PregnancyContext) -> Agent:
        return Agent(
            name="exercise_agent",
            model=self.model_name,
            instructions=create_agent_instructions(context, exercise_agent_base_instructions),
            handoff_description="임신 중 안전한 운동 정보를 제공합니다.",
            input_guardrails=[check_appropriate_content],
            tools=[
                WebSearchTool(user_location={"type": "approximate", "city": "South Korea"}),
                FileSearchTool(
                    max_num_results=5,
                    vector_store_ids=[self.vector_store_id],
                    include_search_results=True,
                )
            ],
        )

    def get_emotional_support_agent(self, context: PregnancyContext) -> Agent:
        return Agent(
            name="emotional_support_agent",
            model=self.model_name,
            instructions=create_agent_instructions(context, emotional_agent_base_instructions),
            handoff_description="임신 중 감정 변화와 심리적 건강을 검색을 통해 지원합니다. 혹은 대화중 나온 내용을 바탕으로 격한 감정을 변화가 감지된다면 사용자에게 조언을 제공합니다.",
            input_guardrails=[check_appropriate_content],
            tools=[
                WebSearchTool(user_location={"type": "approximate", "city": "South Korea"}),
                FileSearchTool(
                    max_num_results=5,
                    vector_store_ids=[self.vector_store_id],
                    include_search_results=True,
                )
            ],
        )

    def get_main_agent(self, context: PregnancyContext, custom_instructions=None) -> Agent:
        """컨텍스트 기반으로 동적으로 메인 에이전트 생성"""
        general_agent = self.get_general_agent(context)
        medical_agent = self.get_medical_agent(context)
        policy_agent = self.get_policy_agent(context)
        nutrition_agent = self.get_nutrition_agent(context)
        exercise_agent = self.get_exercise_agent(context)
        emotional_support_agent = self.get_emotional_support_agent(context)
        
        instructions = custom_instructions or create_agent_instructions(context, main_agent_base_instructions)
        
        main_agent = Agent(
            name="산모 도우미",
            model=self.model_name,
            instructions=instructions,
            handoffs=[
                handoff(agent=general_agent, tool_name_override="transfer_to_general_agent"),
                handoff(agent=medical_agent, tool_name_override="transfer_to_medical_agent"),
                handoff(agent=policy_agent, tool_name_override="transfer_to_policy_agent"),
                handoff(agent=nutrition_agent, tool_name_override="transfer_to_nutrition_agent"),
                handoff(agent=exercise_agent, tool_name_override="transfer_to_exercise_agent"),
                handoff(agent=emotional_support_agent, tool_name_override="transfer_to_emotional_support_agent"),
            ],
            input_guardrails=[check_appropriate_content],
        )
        
        # 디버깅: 사용 가능한 모든 도구 출력
        print("산모 도우미가 사용할 수 있는 도구:")
        if hasattr(main_agent, 'tools') and main_agent.tools:
            for tool in main_agent.tools:
                print(f" - {tool.name}: {tool.description}")
        else:
            print(" - 도구가 없거나 접근할 수 없습니다")
        
        # 핸드오프 목록 확인
        if hasattr(main_agent, 'handoffs') and main_agent.handoffs:
            print("산모 도우미가 사용할 수 있는 핸드오프:")
            for h in main_agent.handoffs:
                print(f" - {h.tool_name if hasattr(h, 'tool_name') else '이름 없음'}")
        else:
            print(" - 핸드오프가 없거나 접근할 수 없습니다")
        
        return main_agent
    
    async def process_query(self, 
                       query_text: str, 
                       user_id: str = None,
                       thread_id: str = None, 
                       pregnancy_week: int = None,
                       baby_name: str = None,
                       stream: bool = False) -> Dict[str, Any]:
        """
        사용자 질문 처리 및 응답 생성
        
        Args:
            query_text: 사용자 질문 텍스트
            user_id: 사용자 ID
            thread_id: 대화 스레드 ID
            pregnancy_week: 임신 주차 (선택적)
            baby_name: 태아 이름 (선택적)
            stream: 스트리밍 응답 여부
            
        Returns:
            생성된 응답 및 메타데이터
        """
        import sys
        import traceback
        
        print(f"========== process_query 시작 (stream={stream}) ==========")
        print(f"thread_id in asyncio: {id(asyncio.current_task())}")
        
        try:
            # 컨텍스트 초기화
            print(f"컨텍스트 초기화: user_id={user_id}, thread_id={thread_id}")
            print(f"질문: {query_text}")
            context = PregnancyContext(user_id=user_id, thread_id=thread_id)
            
            if user_id:
                print("사용자 데이터 로드 시작")
                try:
                    await context.load_user_data_async()
                    print("사용자 데이터 로드 완료")
                except Exception as e:
                    print(f"사용자 데이터 로드 중 오류: {e}")
                    print(traceback.format_exc())
            
            # 추가 정보 설정
            if pregnancy_week:
                context.update_pregnancy_week(pregnancy_week)
            if baby_name:
                context.add_user_info("baby_name", baby_name)
            
            # 훅 초기화
            print("PregnancyAgentHooks 초기화")
            hooks = PregnancyAgentHooks()
            
            # 질문 분류
            print("질문 분류 시작")
            query_classifier = self.get_query_classifier_agent()
            print("질문 분류 에이전트 생성함")
            # try:
            #     classification_result = await Runner.run(
            #         query_classifier,
            #         query_text,
            #         hooks=hooks
            #     )
            #     print(f"질문 분류 완료: {classification_result.final_output.category}")
            # except Exception as e:
            #     print(f"질문 분류 중 오류: {e}")
            #     print(traceback.format_exc())
            #     raise e

            # query_type = classification_result.final_output.category
            # needs_verification = classification_result.final_output.needs_verification

            # 최대 3번 재시도
            for attempt in range(3):
                try:
                    classification_result = await asyncio.wait_for(
                        Runner.run(query_classifier, query_text, hooks=hooks),
                        timeout=5.0
                    )
                    query_type = classification_result.final_output.category
                    needs_verification = classification_result.final_output.needs_verification
                    print(f"질문 쉽게 분류 완료: {query_type}, {needs_verification}")
                    break  # 성공하면 루프 탈출

                except (asyncio.TimeoutError, Exception) as e:
                    print(f"질문 분류 시도 {attempt+1} 실패: {e}")
                    if attempt == 2:  # 마지막 시도
                        # 대체 처리 로직
                        query_type = "general"
                        needs_verification = False
                        print(f"질문 겨우 분류 완료: {query_type}, {needs_verification}")
        
            
            # 메인 에이전트 생성
            print("메인 에이전트 생성")
            main_agent = self.get_main_agent(context)
            
            # 결과 변수
            result_data = {
                "response": "",
                "query_type": query_type,
                "needs_verification": needs_verification,
                "metrics": {}
            }
            
            # 에이전트 실행
            if stream:
                # 스트리밍 응답 (비동기)
                print("스트리밍 모드로 에이전트 실행")
                try:
                    print("Runner.run_streamed 호출 직전")
                    result = Runner.run_streamed(
                        main_agent,
                        query_text,
                        context=context,
                        hooks=hooks
                    )
                    print(f"Runner.run_streamed 반환됨: {type(result)}")
                    
                    # stream_events 메소드 호출 테스트
                    print("stream_events 메소드 테스트")
                    try:
                        # 실제로 호출하진 않고 존재 여부만 확인
                        if hasattr(result, 'stream_events'):
                            print(f"stream_events 메소드 존재")
                            # print(f"stream_events 메소드 존재: {result.stream_events}")
                        else:
                            print("stream_events 메소드가 존재하지 않음!")
                    except Exception as e:
                        print(f"stream_events 메소드 테스트 중 오류: {e}")
                    
                    print("스트리밍 응답 객체 반환 준비")
                    return result
                except Exception as e:
                    print(f"스트리밍 에이전트 실행 중 오류: {e}")
                    print(traceback.format_exc())
                    raise e
            else:
                # 일반 응답
                print("일반 모드로 에이전트 실행")
                result = await Runner.run(
                    main_agent,
                    query_text,
                    context=context,
                    hooks=hooks
                )
                
                # 응답 추출
                response_text = result.final_output
                
                # 검증이 필요한 경우
                if needs_verification:
                    # 데이터 검증 에이전트 실행
                    verification_agent = self.get_data_verification_agent(context)
                    verification_result = await Runner.run(
                        verification_agent,
                        response_text,
                        context=context,
                        hooks=hooks
                    )
                    
                    # 검증 결과 저장
                    validation_result = verification_result.final_output
                    context.add_verification_result(validation_result)
                    
                    # 검증 정보 추가
                    result_data["verification"] = {
                        "is_accurate": validation_result.is_accurate,
                        "confidence_score": validation_result.confidence_score,
                        "reason": validation_result.reason,
                        "corrected_information": validation_result.corrected_information
                    }
                
                # 응답 저장
                result_data["response"] = response_text
                result_data["metrics"] = hooks.get_metrics()
                
                # 대화 내역 저장
                context.add_conversation(query_text, response_text)
                
                # DB에 대화 저장
                conversation = await context.save_to_db_async(query_text, response_text)
                if conversation:
                    result_data["conversation_id"] = conversation.id

                print("일반 응답 반환 준비")
                return result_data
        except Exception as e:
            print(f"process_query 전역 예외: {e}")
            print(traceback.format_exc())
            raise e
        finally:
            print(f"========== process_query 종료 ==========")

# 서비스 인스턴스 생성
openai_agent_service = OpenAIAgentService() 