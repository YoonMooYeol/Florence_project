import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
import time
import re
import httpx
import json
from datetime import date
from agents import Agent, Runner, WebSearchTool, FileSearchTool, trace, handoff, input_guardrail, output_guardrail, GuardrailFunctionOutput
from agents import RunHooks, RunContextWrapper, Usage, Tool, InputGuardrailTripwireTriggered, FunctionTool
from django.conf import settings
from django.db import models
from django.utils import timezone
from .models import LLMConversation, ChatManager
import asyncio
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async

# 환경 변수 로드
load_dotenv()

model_name = os.getenv("LLM_MODEL") or "gpt-4o-mini"
openai_api_key = os.getenv("OPENAI_API_KEY")
vector_store_id = os.getenv("VECTOR_STORE_ID")  # 벡터 스토어 ID


def get_current_date():
    """
    현재 날짜를 'YYYY-MM-DD' 형식으로 반환
    
    Returns:
        str: 현재 날짜 (예: 2024-03-28)
    """
    return date.today().strftime('%Y-%m-%d')

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
        current_time = timezone.now()
        self.event_counter += 1
        tool_key = f"{agent.name}_{tool.name}_{self.event_counter}"
        self.tool_results[tool_key] = {
            "start_time": current_time, 
            "result": None,
            "elapsed_ms": 0
        }
        print(f"도구 사용 시작: {tool.name} ({current_time.strftime('%H:%M:%S.%f')})")
        
    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str) -> None:
        current_time = timezone.now()
        self.event_counter += 1
        tool_key = f"{agent.name}_{tool.name}_{self.event_counter-1}"
        if tool_key in self.tool_results:
            start_time = self.tool_results[tool_key]["start_time"]
            elapsed_ms = (current_time - start_time).total_seconds() * 1000
            self.tool_results[tool_key]["end_time"] = current_time
            self.tool_results[tool_key]["result"] = result
            self.tool_results[tool_key]["elapsed_ms"] = elapsed_ms
            print(f"도구 사용 완료: {tool.name} ({current_time.strftime('%H:%M:%S.%f')}) - 소요시간: {elapsed_ms:.0f}ms")

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
    
    def __init__(self, user_id=None, thread_id=None, auth_token=None):
        self.auth_token = auth_token  # 명시적 필드로 추가
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
        ORM을 비동기 문맥에서 호출할 수 있도록 database_sync_to_async 사용.
        실제 DB에서 사용자 및 임신 정보, 대화 등을 로드.
        """
        from accounts.models import User, Pregnancy
        from .models import ChatManager, LLMConversation
        
        @database_sync_to_async
        def load_all_user_data():
            try:
                user = User.objects.get(user_id=self.user_id)
                
                # 사용자 정보 수집
                user_info = {
                    "name": user.name,
                    "is_pregnant": user.is_pregnant,
                    "email": user.email,
                    "address": user.address,
                }
                
                # 임신 정보 수집
                pregnancy_week = None
                pregnancy = Pregnancy.objects.filter(user=user).order_by('-created_at').first()
                if pregnancy:
                    pregnancy_week = pregnancy.current_week
                    user_info["pregnancy_id"] = str(pregnancy.pregnancy_id)
                    user_info["due_date"] = pregnancy.due_date.isoformat() if pregnancy.due_date else None
                    user_info["baby_name"] = pregnancy.baby_name
                    user_info["high_risk"] = pregnancy.high_risk
                    user_info["address"] = user.address
                
                # 대화 로드
                conversations = []
                if self.thread_id:
                    # 특정 채팅방
                    chat_room = ChatManager.objects.filter(chat_id=self.thread_id).first()
                    if chat_room:
                        conversations = list(LLMConversation.objects.filter(
                            chat_room=chat_room).order_by('-created_at')[:5])
                else:
                    # 사용자의 전체 최근 대화
                    conversations = list(LLMConversation.objects.filter(
                        user=user).order_by('-created_at')[:5])
                
                # 대화 내역 변환
                conversation_history = []
                for conv in reversed(conversations):
                    conversation_history.append({
                        "user": conv.query,
                        "assistant": conv.response,
                        "created_at": conv.created_at.isoformat()
                    })
                    
                return user_info, pregnancy_week, conversation_history
                
            except User.DoesNotExist:
                print(f"사용자 데이터 로드 중 오류: user_id={self.user_id} 해당 사용자가 없습니다.")
                return {}, None, []
        
        # 하나의 트랜잭션으로 모든 데이터 로드
        self.user_info, self.pregnancy_week, self.conversation_history = await load_all_user_data()
        
        # 대화 요약 업데이트
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
        # 최근 5개 대화만 유지
        recent_conversations = self.conversation_history[-5:] if len(self.conversation_history) > 3 else self.conversation_history
        
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
    

# 가드레일 정의
@input_guardrail
def check_appropriate_content(context, agent, input):
    """부적절한 내용이 있는지 확인하는 가드레일"""
    inappropriate_keywords = ["코드카타", '파이썬', '프로그래밍', '코드', '코드 짜줘', '프롬프트']
    
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
6. calendar: 일정 등록에 관한 질문. 모든 일정등록은 일정등록 에이전트에게 넘겨야함. 이전 대화내역을 비교해서 작성을 도와주세요.
7. general: 위 카테고리에 속하지 않는 일반적인 질문. 절대 일정등록을 수행하지 않음.


일정등록은 과거질문내역을 바탕으로 선택하고 데이터를 넘겨야 합니다.
또한 응답에 대한 검증이 필요한지 판단하세요. 의학 정보, 정책 정보, 영양 정보 등 
사실에 기반한 중요한 정보를 제공해야 하는 경우에는 검증이 필요합니다.
주어진 질문에 가장 적합한 카테고리와 검증 필요 여부를 결정하세요.
"""

# 서브에이전트 기본 지시사항
general_agent_base_instructions = """
당신은 일반적인 대화를 제공하는 도우미입니다.
항상 친절한 말로 답변하세요.
의학적인 질문이나 정부 지원 정책에 관한 구체적인 질문은 다른 전문 에이전트에게 넘기세요.
지역이 설정되어있지 않으면 한국지역한정으로 제공하세요.
모든 답변은 한국어로 제공하세요.
"""

medical_agent_base_instructions = """
당신은 임신 주차별 의학 정보를 제공하는 전문가입니다.
사용자의 임신 주차에 맞는 정확한 의학 정보를 제공하세요.
병원찾기나 전문적인 의학지식질문에 검색이나 데이터를 가져와야할때는 WebSearchTool로 검색을 진행하세요.
포함되어야 할 정보는 태아발달, 추가 칼로리, 운동, 영양제, 주차별 받아야할 병원진료 등등을 제공하세요. 제공된 정보는 또 제공될 필요는 없지만 필요하다면 제공하세요.
항상 "이 정보는 일반적인 안내이며, 구체적인 의료 조언은 의사와 상담하세요"라는 면책 조항을 포함하세요.
고위험 임신이라면 고위험 임신에 대한 정보를 추가로 제공하세요.
모든 답변은 한국지역한정, 한국어로 제공하세요.
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
검색이나 데이터를 가져와야할때는 WebSearchTool로 검색을 진행하세요.
고위험 임신이라면 고위험 임신에 대한 정보를 추가로 제공하세요.
맘편한 임신 원스톱 서비스같은 정보를 제공하세요. 그리고 더 많은 정보를 웹검색을 통해 제공하세요. 꼭 지원할수있는 url과 연락처를 제공하세요.
모든 답변은 한국어로 제공하세요.
"""

nutrition_agent_base_instructions = """
당신은 임신 주차별 영양 및 식단 정보를 제공하는 전문가입니다.
검색이나 데이터를 가져와야할때는 WebSearchTool로 검색을 진행하세요.
임신 주차에 따라 필요한 영양소, 권장 식품, 주의해야 할 식품 등에 대한 정보를 제공하세요.
모든 답변은 한국어로 제공하세요.
FileSearchTool에서 가져온 임신 주차별 영양 정보를 활용하세요.
모든 답변은 한국어로 제공하세요.
"""

exercise_agent_base_instructions = """
당신은 임신 중 안전한 운동 정보를 제공하는 전문가입니다.
검색이나 데이터를 가져와야할때는 WebSearchTool로 검색을 진행하세요.
임신 주차에 따른 적절한 운동 유형, 강도, 주의사항 등을 안내하세요.
간단한 스트레칭이나 요가 동작도 설명할 수 있습니다.
고위험 임신이라면 고위험 임신에 대한 정보를 추가로 제공하세요.
FileSearchTool에서 가져온 임신 주차별 운동 정보를 활용하세요.
모든 답변은 한국어로 제공하세요.
"""

emotional_agent_base_instructions = """
당신은 임신 중 감정 변화와 심리적 건강을 지원하는 웹검색 전문가입니다. 현재 이루어진 모든 대화를 분석해서 사용자에게 조언하세요.
검색이나 데이터를 가져와야할때는 WebSearchTool로 검색을 진행하세요.
또는 임신 중 흔히 겪는 감정 변화, 스트레스 관리법, 심리적 안정을 위한 조언을 웹검색을 통해 제공하세요.
공감하는 태도로 따뜻한 지원을 제공하되, 전문적인 심리 상담이 필요한 경우는 전문가의 연락처를 권유하세요.
고위험 임신이라면 고위험 임신에 대한 정보를 추가로 제공하세요.
FileSearchTool에서 가져온 임신 주차별 감정 정보를 활용하세요.
모든 답변은 한국어로 제공하세요.
"""

calendar_agent_base_instructions = """
# 일정 등록 에이전트 프롬프트

## 목적
사용자의 일정 등록 요청을 정확하고 효율적으로 처리합니다.

## 주요 기능
1. 사용자의 자연어 입력을 구조화된 일정 정보로 변환
2. 필수 정보 및 선택적 정보 식별
3. 모호한 정보에 대한 추가 질의

## 처리 가이드라인

### 필수 정보
- 제목 (title): 일정의 핵심을 명확하게 표현
- 시작 날짜 (start_date): 반드시 포함되어야 함

### 일정 및 시간 정보
- 설명 (description): 추가 세부사항
- 시작 시간 (start_time)
- 종료 시간 (end_time)
- 시작 날짜 (start_date)
- 종료 날짜 (end_date)

### 이벤트 컬러 가이드(이벤트타입별로 두개중에 하나 랜덤으로 고르세요.)
    '#FFD600', ['노랑', 'medication'] , 
    '#FF6B6B', ['빨강', 'symptom'] , 
    '#4ECDC4', ['청록', 'exercise'] ,
    '#45B7D1', ['하늘', 'appointment'] ,
    '#96CEB4', ['민트', 'other'] ,
    '#FFEEAD', ['연한 노랑', 'medication'] ,
    '#D4A5A5', ['연한 빨강', 'symptom'] ,
    '#9B59B6', ['보라', 'exercise'] ,
    '#3498DB', ['파랑', 'appointment'] ,
    '#2ECC71', ['초록', 'other'] ,


### 이벤트 타입 분류
- appointment: 공식적인 약속, 미팅
- medication: 약 복용 일정
- symptom: 증상 추적
- exercise: 운동 계획
- other: 위 카테고리에 해당하지 않는 일정

### recurrence_rules json 형식
- 반복 규칙 예시: 
    {
        "pattern": "daily", #/weekly/monthly/yearly 
        "until": "2024-12-31", # 반복 종료 날짜
        "exceptions": ["2024-06-15", "2024-07-01", "2024-08-10"] # 반복 예외 날짜
    }

## 대화 흐름 예시

### 시나리오 1: 명확한 일정
사용자: "다음 주 수요일 오후 3시에 치과 예약"
기대 출력:
```json
{
    "title": "치과 예약",
    "start_date": "2024-04-03",
    "start_time": "15:00",
    "event_type": "appointment",
    "event_color": "#45B7D1"
}
```

### 시나리오 2: 추가 정보 필요
사용자: "다음 주 운동"
에이전트 대응: 
"어떤 종류의 운동인가요? 시간과 장소도 알려주세요."

### 시나리오 3: 복합 일정
사용자: "다음 주 화,목요일 아침 조깅"
기대 출력:
```json
{
    "title": "조깅",
    "start_date": "2024-04-02",
    "end_date": "2024-04-04",
    "start_time": "06:00",
    "event_type": "exercise",
    "event_color": "#2ECC71"
}
```

## 핵심 원칙
1. 사용자 의도 정확히 파악
2. 현재 날짜(today)를 기준으로 해야함
3. 일정 내용은 친구가 써준것처럼 사용자가 행복해지게 써주세요.
4. 시작시간이나 종료시간이 없으면 시작시간은 오후 3시, 종료시간은 오후 4시입니다.  
5. 그외에 정보가 필요하면 일단 랜덤으로 선택하고 실행하세요.
6. 절대 다시물어보지 마세요.

## 오류 처리
- 필수 정보(제목, 날짜) 누락 시 등록 거부
- 날짜/시간 형식 오류 시 사용자에게 확인
- 부적절한 입력에 대해 친절하고 명확한 안내
"""


# 일정 등록에 필요한 데이터 모델
class CalendarEventInput(BaseModel):
    # 추가 속성 금지 설정
    model_config = ConfigDict(extra='forbid')

    # 필수 필드
    title: str = Field(..., description="등록할 일정의 제목")
    start_date: str = Field(..., description="일정 시작 날짜 (YYYY-MM-DD 형식)")

    # 선택 필드
    description: Optional[str] = Field(description="일정 상세 설명")
    start_time: Optional[str] = Field(description="일정 시작 시간 (HH:MM 형식, 24시간제)")
    end_date: Optional[str] = Field(description="일정 종료 날짜 (YYYY-MM-DD 형식)")
    end_time: Optional[str] = Field(description="일정 종료 시간 (HH:MM 형식, 24시간제)")
    event_type: Optional[str] = Field(description="일정 유형 (appointment, medication, symptom, exercise, personal, other)")
    event_color: Optional[str] = Field(description="일정 색상 코드 (예: #FFD600)")

class CalendarTool(FunctionTool):
    """일정 등록을 위한 도구"""
    
    def __init__(self):
        tool_name = "CalendarTool"
        tool_description = "캘린더에 새 일정을 등록합니다. 일정 제목과 시작 날짜(YYYY-MM-DD)는 필수입니다. 시작시간밖에 없으면 종료시간은 한시간뒤로 설정하시고, 그외에 정보가 필요하면 일단 랜덤으로 선택하고 실행하세요."

        # Pydantic 모델에서 스키마 생성
        tool_params_schema = CalendarEventInput.model_json_schema()

        super().__init__(
            name=tool_name,
            description=tool_description,
            params_json_schema=tool_params_schema,
            on_invoke_tool=self.run
        )
        
        # 환경에 따른 API 엔드포인트 설정
        if os.getenv("DJANGO_ENV") == "development":
            self.api_endpoint = os.getenv("CALENDAR_API_ENDPOINT_DEV", "http://127.0.0.1:8000/v1/calendars/events/")
        else:
            self.api_endpoint = os.getenv("CALENDAR_API_ENDPOINT_PROD", "https://nooridal.click/v1/calendars/events/")
        
        print(f"CalendarTool initialized. API Endpoint: {self.api_endpoint}")

    async def run(self, context: RunContextWrapper, tool_input: Union[CalendarEventInput, str, Dict]) -> str:
        print(f"CalendarTool 실행 시작. 받은 tool_input 타입: {type(tool_input)}")
        
        # 인증 토큰 접근 - RunContextWrapper.context에서 가져오기
        auth_token = None
        
        # context.context에 접근 (이것이 원래 전달한 객체)
        if hasattr(context, 'context'):
            original_context = context.context
            print(f"원본 컨텍스트 타입: {type(original_context)}")
            
            # 딕셔너리인 경우
            if isinstance(original_context, dict):
                auth_token = original_context.get('auth_token')
                print("딕셔너리 컨텍스트에서 auth_token 키로 접근")
            
            # PregnancyContext 객체인 경우
            elif hasattr(original_context, 'auth_token'):
                auth_token = original_context.auth_token
                print("객체 컨텍스트에서 auth_token 속성으로 접근")
        
        # 헤더 설정
        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
            print(f"토큰을 성공적으로 찾았습니다! (길이: {len(auth_token)})")
        else:
            print("인증 토큰을 찾을 수 없습니다. context.context에 없습니다.")
            return "인증 토큰이 필요합니다. 로그인 상태를 확인해주세요."
        
        # 입력 변환 처리
        instance: Optional[CalendarEventInput] = None
        if isinstance(tool_input, CalendarEventInput):
            instance = tool_input
        elif isinstance(tool_input, dict):
            try:
                instance = CalendarEventInput(**tool_input)
                print("참고: Dict에서 CalendarEventInput 인스턴스 생성됨.")
            except Exception as e:
                print(f"오류: Dict에서 CalendarEventInput 인스턴스 생성 실패: {e}")
                return f"오류: 일정 정보를 처리하는 중 형식이 맞지 않아 실패했습니다."
        elif isinstance(tool_input, str):
            try:
                json_match = re.search(r'\{.*\}', tool_input, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                    instance = CalendarEventInput(**data)
                    print("참고: JSON 문자열에서 CalendarEventInput 인스턴스 생성됨.")
                else:
                    print("오류: 입력 문자열에서 유효한 JSON 객체를 찾을 수 없음.")
                    return "오류: 일정 정보를 인식할 수 없습니다."
            except Exception as e:
                print(f"오류: JSON 문자열 파싱 또는 CalendarEventInput 인스턴스 생성 실패: {e}")
                return f"오류: 일정 정보 처리 중 오류가 발생했습니다."
        else:
            return f"오류: 죄송합니다, 일정 요청을 처리할 수 없습니다."

        if not instance:
            return "오류: 일정 정보를 처리하지 못했습니다."

        payload = instance.model_dump(exclude_none=True)
        print(f"CalendarTool Payload: {payload}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=120
                )
                print(f"CalendarTool API 응답 상태: {response.status_code}")
                response.raise_for_status()

            if response.status_code == 201:
                result = f"{response.json().get('title')} 일정이 등록되었습니다."
            else:
                result = "일정 등록에 실패했습니다."
            
            
            print(f"CalendarTool 성공: {result}")
            return result

        except httpx.TimeoutException:
            error_msg = f"일정 등록 실패: 서버 연결 시간 초과"
            print(f"CalendarTool 오류: {error_msg}")
            return error_msg
        except httpx.ConnectError:
            error_msg = f"일정 등록 실패: 서버에 연결할 수 없습니다."
            print(f"CalendarTool 오류: {error_msg}")
            return error_msg
        except httpx.RequestError as e:
            error_msg = f"일정 등록 중 네트워크 오류 발생"
            print(f"CalendarTool 오류: {error_msg}: {e}")
            return error_msg
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                error_msg = "오류: 사용자 인증에 실패했습니다. 다시 로그인해주세요."
                print(f"CalendarTool 인증 오류 (401)")
            else:
                error_detail = f"HTTP {e.response.status_code} 오류"
                try:
                    error_data = e.response.json()
                    error_detail += f" - {error_data.get('detail', str(error_data))}"
                except:
                    error_detail += f" - {e.response.text[:100]}"
                error_msg = f"일정 등록 실패: {error_detail}"
                print(f"CalendarTool 오류: {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"일정 등록 중 예상치 못한 오류 발생"
            print(f"CalendarTool 오류: {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg

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
            input_guardrails=[check_appropriate_content],
            output_type=QueryClassification
        )

    # 데이터 검증 에이전트 정의
    def get_data_verification_agent(self, context: PregnancyContext) -> Agent:
        return Agent(
            name="data_verification_agent",
            model=self.model_name,
            instructions=create_agent_instructions(context, data_verification_agent_base_instructions),
            input_guardrails=[check_appropriate_content],
            output_type=DataValidationResult
        )

    # 서브에이전트 정의 
    def get_general_agent(self, context: PregnancyContext) -> Agent:
        return Agent(
            name="general_agent",
            model=self.model_name,
            instructions=create_agent_instructions(context, general_agent_base_instructions),
            handoff_description="일반적인 대화를 제공합니다.",
            tools=[WebSearchTool(user_location={"type": "approximate", "city": "korea"}), CalendarTool()],
            input_guardrails=[check_appropriate_content],
        )

    def get_medical_agent(self, context: PregnancyContext) -> Agent:
        return Agent(
            name="medical_agent",
            model=self.model_name,
            instructions=create_agent_instructions(context, medical_agent_base_instructions),
            handoff_description="임신 주차별 의학 정보와 병원 정보를 제공합니다.",
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
            tools=[WebSearchTool(user_location={"type": "approximate", "city": "korea"})],
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
                WebSearchTool(user_location={"type": "approximate", "city": "korea"}),
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
                WebSearchTool(user_location={"type": "approximate", "city": "korea"}),
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
                WebSearchTool(user_location={"type": "approximate", "city": "korea"}),
                FileSearchTool(
                    max_num_results=5,
                    vector_store_ids=[self.vector_store_id],
                    include_search_results=True,
                )
            ],
        )
    def get_calendar_agent(self, context: PregnancyContext) -> Agent:
            """일정 등록 에이전트를 생성합니다."""
            return Agent(
            name="calendar_agent",
            model=self.model_name,
            instructions=create_agent_instructions(context, calendar_agent_base_instructions),
            handoff_description="캘린더에 일정을 등록합니다.",
            tools=[CalendarTool()],
            input_guardrails=[check_appropriate_content],
        )
    
    async def process_query(self, 
                        query_text: str, 
                        user_id: str = None,
                        thread_id: str = None, 
                        auth_token: Optional[str] = None,
                        pregnancy_week: int = None,
                        baby_name: str = None,
                        high_risk: bool = None,
                        address: str = None,
                        stream: bool = False,
                        today: str = get_current_date()) -> Dict[str, Any]:
                        
        
        """
        사용자 질문 처리 및 응답 생성
        """
        import sys
        import traceback
        
        run_start_time = time.time()
        print(f"========== process_query 시작 (stream={stream}) ==========")
        
        try:
            # 컨텍스트 초기화
            context = PregnancyContext(user_id=user_id, thread_id=thread_id)
            
            # auth_token을 PregnancyContext 객체에 직접 추가
            if auth_token:
                context.auth_token = auth_token  # 명시적 속성으로 추가
                print(f"PregnancyContext에 auth_token 추가됨 (길이: {len(auth_token)})")
            
            # 사용자 데이터 로드
            if user_id:
                await context.load_user_data_async()
            
            # 추가 정보 설정
            if pregnancy_week:
                context.update_pregnancy_week(pregnancy_week)
            if high_risk:
                context.add_user_info("high_risk", high_risk)
            if baby_name:
                context.add_user_info("baby_name", baby_name)
            if address:
                context.add_user_info("address", address)
            context.add_user_info("today", today)
            # 훅 초기화
            hooks = PregnancyAgentHooks()
            
            # 질문 분류
            start_time = time.time()
            print(f"[{time.time() - start_time:.2f}s] 질문 분류 시작")
            query_classifier = self.get_query_classifier_agent()
            print("질문 분류 에이전트 생성함")

            # 최대 3번 재시도
            for attempt in range(3):
                try:
                    classification_result = await asyncio.wait_for(
                        Runner.run(query_classifier, query_text, hooks=hooks),
                        timeout=5.0
                    )
                    query_type = classification_result.final_output.category
                    needs_verification = classification_result.final_output.needs_verification
                    print(f"[{time.time() - start_time:.2f}s] 질문 분류 완료: {query_type}")
                    break  # 성공하면 루프 탈출

                except (asyncio.TimeoutError, Exception) as e:
                    print(f"질문 분류 시도 {attempt+1} 실패: {e}")
                    if attempt == 2:  # 마지막 시도
                        # 대체 처리 로직
                        query_type = "general"
                        needs_verification = False
                        print(f"질문 분류 완료: {query_type}, {needs_verification}")
        
            # 일정 관련 키워드 탐지
            calendar_keywords = ["일정", "등록", "캘린더", "약속", "기록", "메모", "리마인더", "알림", "추가", "예약"]
            
            # 분류 결과에 따라 바로 적절한 에이전트 선택
            if query_type == "medical":
                agent_to_use = self.get_medical_agent(context)
            elif query_type == "policy":
                agent_to_use = self.get_policy_agent(context)
            elif query_type == "nutrition":
                agent_to_use = self.get_nutrition_agent(context)
            elif query_type == "exercise":
                agent_to_use = self.get_exercise_agent(context)
            elif query_type == "emotional":
                agent_to_use = self.get_emotional_support_agent(context)
            elif query_type == "calendar":
                agent_to_use = self.get_calendar_agent(context)
            else:  # general 또는 기타
                agent_to_use = self.get_general_agent(context)
                print("general 또는 기타 에이전트 선택됨")

            # 에이전트 선택 지점
            print(f"[{time.time() - run_start_time:.2f}s] {query_type} 에이전트 선택됨")

            # 에이전트 실행 - context 객체 그대로 전달
            if stream:
                try:
                    result = Runner.run_streamed(
                        agent_to_use,
                        query_text,
                        context=context,  # PregnancyContext 객체 직접 전달
                        hooks=hooks
                    )
                    # 스트리밍 응답과 함께 needs_verification 정보 전달
                    result.needs_verification = needs_verification
                    result.query_type = query_type
                    return result
                except InputGuardrailTripwireTriggered:
                    # 가드레일 트립와이어가 발동된 경우 커스텀 스트리밍 응답 반환
                    from agents import StreamEvent, ModelChunkEvent
                    
                    # 가드레일 메시지 생성
                    guardrail_message = "임신과 관련된 질문이나 대화를 입력해주세요"
                    
                    # 가짜 스트리밍 이벤트 생성
                    async def guardrail_stream():
                        yield StreamEvent(type="start")
                        yield ModelChunkEvent(content=guardrail_message)
                        yield StreamEvent(type="end")
                    
                    # 스트리밍 응답 객체 생성
                    from agents import StreamingAgentOutput
                    result = StreamingAgentOutput(stream=guardrail_stream())
                    result.needs_verification = needs_verification
                    result.query_type = query_type
                    return result
        except Exception as e:
            print(f"process_query 전역 예외: {e}")
            print(traceback.format_exc())
            raise e
        finally:
            print(f"========== process_query 종료 ==========")



# 서비스 인스턴스 생성
openai_agent_service = OpenAIAgentService() 