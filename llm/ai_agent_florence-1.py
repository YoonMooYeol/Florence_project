import asyncio
import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from agents import Agent, Runner, WebSearchTool, FileSearchTool, trace, handoff, input_guardrail, output_guardrail, GuardrailFunctionOutput
from agents import RunHooks, RunContextWrapper, Usage, Tool
from openai.types.responses import ResponseTextDeltaEvent

# 환경 변수 로드
load_dotenv()

model_name = os.getenv("MODEL_NAME")
openai_api_key = os.getenv("OPENAI_API_KEY")
vector_store_id = os.getenv("VECTOR_STORE_ID")  # 벡터 스토어 ID 추가

# 라이프사이클 추적을 위한 훅 클래스 추가
class PregnancyAgentHooks(RunHooks):
    def __init__(self):
        self.event_counter = 0

    async def on_agent_start(self, context: RunContextWrapper, agent: Agent) -> None:
        self.event_counter += 1
        print(f"선택된 에이전트 [{agent.name}]")


    async def on_agent_end(self, context: RunContextWrapper, agent: Agent, output: Any) -> None:
        self.event_counter += 1

    async def on_handoff(self, context: RunContextWrapper, from_agent: Agent, to_agent: Agent) -> None:
        self.event_counter += 1
        print(f"\n* 핸드오프 [{from_agent.name}] -> [{to_agent.name}]")
        
    async def on_tool_start(self, context: RunContextWrapper, agent: Agent, tool: Tool) -> None:
        self.event_counter += 1
        
    async def on_tool_end(self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str) -> None:
        self.event_counter += 1
        print(f"\n* 툴 종료 [{tool.name}: {result}]")


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

# 컨텍스트 모델 정의
class PregnancyContext:
    """임신 관련 정보를 저장하는 컨텍스트 클래스"""
    
    def __init__(self):
        self.pregnancy_week: Optional[int] = None
        self.user_info: Dict[str, Any] = {}
        self.conversation_history: List[Dict[str, Any]] = []
        self.conversation_summary: str = ""
        self.verification_results: List[DataValidationResult] = []
        
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
            "assistant": assistant_output
        })
        
        # 대화 요약 업데이트 (최근 3개 대화만 유지)
        recent_conversations = self.conversation_history[-3:] if len(self.conversation_history) > 3 else self.conversation_history
        
        summary = "이전 대화 내용:\n"
        for i, conv in enumerate(recent_conversations):
            summary += f"사용자: {conv['user']}\n"
            summary += f"어시스턴트: {conv['assistant']}\n\n"
        
        self.conversation_summary = summary
    
    def add_verification_result(self, result: DataValidationResult):
        """정보 검증 결과 추가"""
        self.verification_results.append(result)

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
    
    # 대화 기록이 있다면 추가
    if context.conversation_history:
        instructions += f"\n\n{context.conversation_summary}"
    
    return instructions

# 질문 분류 에이전트 지시사항 추가
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

# 서브에이전트 기본 지시사항 (변경 없음)
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

main_agent_base_instructions = """
당신은 임신과 출산에 관한 정보를 제공하는 산모 도우미입니다.
사용자의 질문을 분석하고 적절한 전문 에이전트에게 연결하세요.

다음은 각 에이전트의 전문 분야입니다:
1. general_agent: 임신과 출산에 관한 일반적인 정보
2. medical_agent: 임신 주차별 의학 정보 
3. policy_agent: 정부 지원 정책 정보
4. nutrition_agent: 임신 중 영양 및 식단 정보
5. exercise_agent: 임신 중 안전한 운동 정보
6. emotional_support_agent: 임신 중 감정 변화와 심리적 건강 지원

사용자가 특정 주차에 대한 정보를 요청하면 해당 정보를 기억하고 이후 대화에 활용하세요.
사용자의 질문에 가장 적합한 에이전트에게 전달하세요.
모든 답변은 한국어로 제공하세요.
"""

# 질문 분류 에이전트 정의
def get_query_classifier_agent() -> Agent:
    return Agent(
        name="query_classifier_agent",
        instructions=query_classifier_instructions,
        output_type=QueryClassification
    )

# 데이터 검증 에이전트 정의
def get_data_verification_agent(context: PregnancyContext) -> Agent:
    return Agent(
        name="data_verification_agent",
        model="gpt-4o",
        instructions=create_agent_instructions(context, data_verification_agent_base_instructions),
        output_type=DataValidationResult
    )

# 서브에이전트 정의 
def get_general_agent(context: PregnancyContext) -> Agent:
    return Agent(
        name="general_agent",
        model=model_name,
        instructions=create_agent_instructions(context, general_agent_base_instructions),
        handoff_description="일반적인 대화를 제공합니다.",
        input_guardrails=[check_appropriate_content],
    )

def get_medical_agent(context: PregnancyContext) -> Agent:
    return Agent(
        name="medical_agent",
        model="gpt-4o",
        instructions=create_agent_instructions(context, medical_agent_base_instructions),
        handoff_description="임신 주차별 의학 정보를 제공합니다.",
        input_guardrails=[check_appropriate_content],
        output_guardrails=[verify_medical_advice],
        tools=[
            WebSearchTool(),
            FileSearchTool(
                max_num_results=5,
                vector_store_ids=[vector_store_id],
                include_search_results=True,
            )
        ],
    )

def get_policy_agent(context: PregnancyContext) -> Agent:
    return Agent(
        name="policy_agent",
        model="gpt-4o",
        instructions=create_agent_instructions(context, policy_agent_base_instructions),
        handoff_description="임신과 출산 관련 정부 지원 정책 정보와 연락처를 제공합니다.",
        tools=[WebSearchTool(user_location={"type": "approximate", "city": "South Korea"})],
        input_guardrails=[check_appropriate_content],
    )

def get_nutrition_agent(context: PregnancyContext) -> Agent:
    return Agent(
        name="nutrition_agent",
        model=model_name,
        instructions=create_agent_instructions(context, nutrition_agent_base_instructions),
        handoff_description="임신 주차별 영양 및 식단 정보를 제공합니다.",
        input_guardrails=[check_appropriate_content],
        tools=[
            WebSearchTool(user_location={"type": "approximate", "city": "South Korea"}),
            FileSearchTool(
                max_num_results=5,
                vector_store_ids=[vector_store_id],
                include_search_results=True,
            )
        ],
    )

def get_exercise_agent(context: PregnancyContext) -> Agent:
    return Agent(
        name="exercise_agent",
        model=model_name,
        instructions=create_agent_instructions(context, exercise_agent_base_instructions),
        handoff_description="임신 중 안전한 운동 정보를 제공합니다.",
        input_guardrails=[check_appropriate_content],
        tools=[
            WebSearchTool(user_location={"type": "approximate", "city": "South Korea"}),
            FileSearchTool(
                max_num_results=5,
                vector_store_ids=[vector_store_id],
                include_search_results=True,
            )
        ],
    )

def get_emotional_support_agent(context: PregnancyContext) -> Agent:
    return Agent(
        name="emotional_support_agent",
        model="gpt-4o",
        instructions=create_agent_instructions(context, emotional_agent_base_instructions),
        handoff_description="임신 중 감정 변화와 심리적 건강을 검색을 통해 지원합니다. 혹은 대화중 나온 내용을 바탕으로 격한 감정을 변화가 감지된다면 사용자에게 조언을 제공합니다.",
        input_guardrails=[check_appropriate_content],
        tools=[
            WebSearchTool(user_location={"type": "approximate", "city": "South Korea"}),
            FileSearchTool(
                max_num_results=5,
                vector_store_ids=[vector_store_id],
                include_search_results=True,
            )
        ],
    )

def get_main_agent(context: PregnancyContext) -> Agent:
    """컨텍스트 기반으로 동적으로 메인 에이전트 생성"""
    general_agent = get_general_agent(context)
    medical_agent = get_medical_agent(context)
    policy_agent = get_policy_agent(context)
    nutrition_agent = get_nutrition_agent(context)
    exercise_agent = get_exercise_agent(context)
    emotional_support_agent = get_emotional_support_agent(context)
    
    return Agent(
        name="산모 도우미",
        model=model_name,
        instructions=create_agent_instructions(context, main_agent_base_instructions),
        handoffs=[
            handoff(general_agent),
            handoff(medical_agent),
            handoff(policy_agent),
            handoff(nutrition_agent),
            handoff(exercise_agent),
            handoff(emotional_support_agent),
        ],
        input_guardrails=[check_appropriate_content],
    )

# 텍스트 스트리밍 시뮬레이션 함수
async def stream_text(text: str, delay: float = 0.001):
    """텍스트를 스트리밍 형태로 출력하는 함수"""
    for char in text:
        print(char, end="", flush=True)
        await asyncio.sleep(delay)
    print()

# 응답 검증 및 출력 함수
async def process_and_verify_response(context: PregnancyContext, initial_response: str, query_type: str, needs_verification: bool, hooks: PregnancyAgentHooks):
    """응답을 검증하고 적절한 방식으로 출력하는 함수"""
    if not needs_verification:
        return initial_response
    
    # 응답 검증
    verification_agent = get_data_verification_agent(context)
    verification_result = await Runner.run(
        verification_agent,
        initial_response,
        context=context,
        hooks=hooks  # 훅 전달
    )
    
    result = verification_result.final_output
    context.add_verification_result(result)
    
    # 검증 결과에 따라 응답 조정

    final_response = initial_response

    # 검증된 정보 출력 - 여러 출력을 하나로 합침
    print(f"\n📋 정보 신뢰도: {result.confidence_score:.1f}")
    await stream_text(final_response, delay=0.0005)
    
    return final_response


async def main():
    # 컨텍스트 생성
    context = PregnancyContext()
    
    # 라이프사이클 훅 초기화 - 디버그 모드 설정 가능
    hooks = PregnancyAgentHooks()
    
    print("========== 산모 도우미 에이전트 ==========")
    print("안녕하세요! 임신과 출산에 관한 정보를 제공하는 산모 도우미입니다.")
    print("질문을 입력해주세요. 종료하려면 'q'를 입력하세요.")
    print("===========================================")
    
    # 질문 분류 에이전트 초기화
    query_classifier = get_query_classifier_agent()
    
    with trace("산모 도우미 에이전트"):
        while True:
            print(f"현재 임신 주차: {context.pregnancy_week}")
            print(f"현재 사용자 정보: {context.user_info}")
            user_input = input("\n질문: ")
            
            if user_input.lower() == 'q':
                print("대화를 종료합니다. 언제든지 다시 찾아주세요!")
                break

            # 1단계: 질문 분류
            print("\n🔍 질문 분류 중...", end="", flush=True)
            classification_result = await Runner.run(
                query_classifier,
                user_input,
                hooks=hooks  # 훅 전달
            )
            
            query_type = classification_result.final_output.category
            needs_verification = classification_result.final_output.needs_verification
            print(f"\r\n✳️ 질문 유형: {query_type} (검증 필요: {'예' if needs_verification else '아니오'})")
            
            # 2단계: 에이전트로부터 초기 응답 생성
            main_agent = get_main_agent(context)
            
            # 스트리밍 방식으로 에이전트 실행
            print(f"\n🤖 답변 생성 중...", end="", flush=True)
            result = Runner.run_streamed(
                main_agent,
                user_input,
                context=context,
                hooks=hooks  # 훅 전달
            )
            
            # 메시지 지우기
            print("\r" + " " * 30 + "\r", end="")
            
            # 스트리밍으로 초기 응답 수집
            initial_response = ""
            if not needs_verification:
                # 검증이 필요하지 않으면 바로 스트리밍 출력
                async for event in result.stream_events():
                    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                        print(event.data.delta, end="", flush=True)
                        initial_response += event.data.delta
                
                final_response = initial_response
            else:
                # 검증이 필요하면 먼저 응답 수집 후 검증
                async for event in result.stream_events():
                    if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                        initial_response += event.data.delta
                
                # 3단계: 응답 검증 및 출력
                final_response = await process_and_verify_response(
                    context, 
                    initial_response, 
                    query_type,
                    needs_verification,
                    hooks  # 훅 전달
                )
            
            print()  # 단일 줄바꿈으로 충분
            
            # 최종 응답 컨텍스트에 저장
            context.add_conversation(user_input, final_response)

if __name__ == "__main__":
    asyncio.run(main())