import os
import json
import tiktoken
from typing import TypedDict, List, Dict, Any, Optional
import uuid

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_core.documents import Document
from langchain_core.messages import get_buffer_string, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai.embeddings import OpenAIEmbeddings
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

class Message(TypedDict):
    role: str
    content: str

class State(MessagesState):
    pregnancy_week: int
    recall_memories: List[str]

class Florence:
    def __init__(self, 
                 openai_api_key: Optional[str] = None,
                 tavily_api_key: Optional[str] = None,
                 google_api_key: Optional[str] = None,
                 anthropic_api_key: Optional[str] = None,
                 model_name: str = "gpt-4o-mini",
                 pregnancy_data_path: str = "pregnancy.csv"):
        """
        플로렌스 임신정보 어시스턴트 초기화
        
        Args:
            openai_api_key: OpenAI API 키
            tavily_api_key: Tavily 검색 API 키
            google_api_key: Google API 키
            anthropic_api_key: Anthropic API 키
            model_name: 사용할 LLM 모델 이름
            pregnancy_data_path: 임신 정보 CSV 파일 경로
        """
        # API 키 설정
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.tavily_api_key = tavily_api_key or os.environ.get("TAVILY_API_KEY")
        self.google_api_key = google_api_key or os.environ.get("GOOGLE_API_KEY")
        self.anthropic_api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        # 필요한 환경 변수 설정
        if self.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.openai_api_key
        if self.tavily_api_key:
            os.environ["TAVILY_API_KEY"] = self.tavily_api_key
        if self.google_api_key:
            os.environ["GOOGLE_API_KEY"] = self.google_api_key
        if self.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.anthropic_api_key
            
        os.environ["USER_AGENT"] = "Florence/1.0 (http://example.com)"
        
        # 데이터 경로 설정
        self.pregnancy_data_path = pregnancy_data_path
        
        # 벡터 스토어 초기화
        self.recall_vector_store = InMemoryVectorStore(OpenAIEmbeddings())
        
        # 모델 초기화
        self.model_name = model_name
        self.rate_limiter = InMemoryRateLimiter(
            requests_per_second=0.167,  # 분당 10개 요청
            check_every_n_seconds=0.1,  # 0.1초마다 요청 횟수 체크
            max_bucket_size=10,  # 최대 10개 요청 저장
        )
        
        self.llm = ChatOpenAI(
            model=self.model_name,
            rate_limiter=self.rate_limiter,
        )
        
        # 토크나이저 초기화
        self.tokenizer = tiktoken.encoding_for_model(self.model_name)
        
        # 도구 및 에이전트 초기화
        self.tools = self._initialize_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # 시스템 프롬프트 정의
        self.prompt = self._create_prompt()
        
        # 그래프 빌더 및 에이전트 초기화
        self.agent_executor = self._build_graph()
        
        # 출력 상태 플래그 초기화
        self.initialized_output = False
        self.showed_agent_header = False
        self.showed_tools_header = False
        self.showed_tool_result = False
    
    def _initialize_tools(self):
        """도구 함수 초기화"""
        @tool
        def retrieve_pregnancy_info(pregnancy_week: int):
            """임신 주차를 기반으로 임신 정보를 검색합니다."""
            # 데이터 로드
            loader = CSVLoader(file_path=self.pregnancy_data_path, csv_args={
                "delimiter": ",",
                "quotechar": '"',
            })
            data = loader.load()
            # 검색 결과를 Retrieve 형식으로 반환
            return data[pregnancy_week-1]
        
        @tool
        def tavily_search(query: str, state: dict = None):
            """타비레이 검색 도구를 사용하여 2025년 현재 지원중인 산모 지원 정책 웹 검색을 수행합니다."""
            tavily_search_tool = TavilySearchResults(max_results=5)
            result = tavily_search_tool.invoke(query)
            return result
        
        @tool
        def save_recall_memory(memory: str, config: RunnableConfig) -> str:
            """Save memory to vectorstore for later semantic retrieval."""
            user_id = self._get_user_id(config)
            document = Document(
                page_content=memory, id=str(uuid.uuid4()), metadata={"user_id": user_id}
            )
            self.recall_vector_store.add_documents([document])
            return memory
        
        @tool
        def search_recall_memories(query: str, config: RunnableConfig) -> List[str]:
            """Search for relevant memories."""
            user_id = self._get_user_id(config)
        
            def _filter_function(doc: Document) -> bool:
                return doc.metadata.get("user_id") == user_id
        
            documents = self.recall_vector_store.similarity_search(
                query, k=3, filter=_filter_function
            )
            return [document.page_content for document in documents]
        
        return [retrieve_pregnancy_info, tavily_search, save_recall_memory, search_recall_memories]
    
    def _get_user_id(self, config: RunnableConfig) -> str:
        """사용자 ID 추출"""
        user_id = config["configurable"].get("user_id")
        if user_id is None:
            raise ValueError("User ID needs to be provided to save a memory.")
        return user_id
    
    def _create_prompt(self):
        """시스템 프롬프트 생성"""
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant with advanced long-term memory"
                    " capabilities. Powered by a stateless LLM, you must rely on"
                    " external memory to store information between conversations."
                    " Utilize the available memory tools to store and retrieve"
                    " important details that will help you better attend to the user's"
                    " needs and understand their context.\n\n"
                    "Memory Usage Guidelines:\n"
                    "1. Actively use memory tools (save_core_memory, save_recall_memory)"
                    " to build a comprehensive understanding of the user.\n"
                    "2. Make informed suppositions and extrapolations based on stored"
                    " memories.\n"
                    "3. Regularly reflect on past interactions to identify patterns and"
                    " preferences.\n"
                    "4. Update your mental model of the user with each new piece of"
                    " information.\n"
                    "5. Cross-reference new information with existing memories for"
                    " consistency.\n"
                    "6. Prioritize storing emotional context and personal values"
                    " alongside facts.\n"
                    "7. Use memory to anticipate needs and tailor responses to the"
                    " user's style.\n"
                    "8. Recognize and acknowledge changes in the user's situation or"
                    " perspectives over time.\n"
                    "9. Leverage memories to provide personalized examples and"
                    " analogies.\n"
                    "10. Recall past challenges or successes to inform current"
                    " problem-solving.\n\n"
                    "## Recall Memories\n"
                    "Recall memories are contextually retrieved based on the current"
                    " conversation:\n{recall_memories}\n\n"
                    "## Instructions\n"
                    "Engage with the user naturally, as a trusted colleague or friend."
                    " There's no need to explicitly mention your memory capabilities."
                    " Instead, seamlessly incorporate your understanding of the user"
                    " into your responses. Be attentive to subtle cues and underlying"
                    " emotions. Adapt your communication style to match the user's"
                    " preferences and current emotional state. Use tools to persist"
                    " information you want to retain in the next conversation. If you"
                    " do call tools, all text preceding the tool call is an internal"
                    " message. Respond AFTER calling the tool, once you have"
                    " confirmation that the tool completed successfully.\n\n"
                    "**For simple conversations, use the `talk` tool to respond quickly.**"
                    "Limit responses strictly to topics related to pregnant women. Do not engage in discussions unrelated to maternity, pregnancy, or postpartum care."
                    " When providing a URL, include it at the end of your response. Additionally, Only display the website domain."
                ),
                ("placeholder", "{messages}"),
            ]
        )
    
    def _agent(self, state: State):
        """에이전트 노드 처리 함수"""
        bound_prompt = self.prompt | self.llm_with_tools
        recall_str = (
            "<recall_memory>\n" + "\n".join(state["recall_memories"]) + "\n</recall_memory>"
        )
        prediction = bound_prompt.invoke(
            {
                "messages": state["messages"],
                "recall_memories": recall_str,
            }
        )
        
        return {"messages": [prediction]}
    
    def _load_memories(self, state: State, config: RunnableConfig) -> State:
        """메모리 로드 함수"""
        convo_str = get_buffer_string(state["messages"])
        convo_str = self.tokenizer.decode(self.tokenizer.encode(convo_str)[:2048])
        
        # 도구 직접 호출
        recall_memories = []
        try:
            for tool in self.tools:
                if tool.name == "search_recall_memories":
                    recall_memories = tool.invoke({"query": convo_str, "config": config})
                    break
        except Exception as e:
            print(f"메모리 로드 중 오류 발생: {e}")
        
        # 기존 상태와 결합해 업데이트
        state["recall_memories"] = recall_memories
        return state
    
    def _route_tools(self, state: State):
        """도구 라우팅 함수"""
        msg = state["messages"][-1]
        if msg.tool_calls:
            return "tools"
        return END
    
    def _build_graph(self):
        """그래프 빌드 및 컴파일"""
        builder = StateGraph(State)
        builder.add_node("load_memories", self._load_memories)
        builder.add_node("agent", self._agent)
        builder.add_node("tools", ToolNode(self.tools))
        
        # 엣지 추가
        builder.add_edge(START, "load_memories")
        builder.add_edge("load_memories", "agent")
        builder.add_conditional_edges("agent", self._route_tools, ["tools", END])
        builder.add_edge("tools", "agent")
        
        # 그래프 컴파일
        memory = MemorySaver()
        return builder.compile(checkpointer=memory)
    
    def clean_stream_output(self, step, metadata):
        """스트림 출력 정리 함수"""
        node_name = metadata.get("langgraph_node", "unknown")
    
        # 처음 함수가 호출될 때 속성 초기화
        if not self.initialized_output:
            self.initialized_output = True
            self.showed_agent_header = False
            self.showed_tools_header = False
            self.showed_tool_result = False
    
        # 도구 사용 감지 - 한 번만 표시
        if node_name == "agent" and hasattr(step, 'tool_calls') and step.tool_calls:
            if not self.showed_tools_header:
                self.showed_tools_header = True
                
                print("\n정보 검색툴:")
                for tool_call in step.tool_calls:
                    tool_name = tool_call.get('name', 'unknown')
                    print(f"  • {tool_name}")
    
        # 도구 결과 - 한 번만 표시
        elif node_name == "tools":
            if not self.showed_tool_result:
                self.showed_tool_result = True
                
                if hasattr(step, 'content') and step.content:
                    content = step.content
                    
                    # 타빌리 검색 결과인지 확인 (JSON 배열 형태로 시작하는지)
                    if isinstance(content, str) and content.strip().startswith("[{"):
                        try:
                            # JSON 파싱
                            results = json.loads(content)
                            
                            print("\n📊 검색 결과:")
                            print("──────────────────────────────────────")
                            for i, result in enumerate(results, 1):
                                print(f"[{i}] {result.get('title', '제목 없음')}")
                                print(f" {result.get('url', '링크 없음')}")
                                print(f" {result.get('content', '내용 없음')[:150]}...")
                                print("──────────────────────────────────────")
                        except:
                            # 파싱 실패 시 원본 출력
                            print(f"\n검색 결과: {content}")
                            print("──────────────────────────────────────")
                    
                    # 일반 검색 결과 (retrieve_pregnancy_info 등)인 경우
                    else:
                        # page_content= 부분 제거
                        if "page_content=" in content:
                            content = content.replace("page_content='", "")
                            content = content.replace("page_content=", "")
                            # 마지막 따옴표와 뒤의 메타데이터 부분 제거
                            if "', metadata=" in content:
                                content = content.split("', metadata=")[0]
                            elif "metadata=" in content:
                                content = content.split("metadata=")[0]
                        
                        print(f"\n참조 정보: {content}")
                        print("──────────────────────────────────────")
    
        # AI 응답 - 처음에만 헤더를 표시하고 이후에는 텍스트만 누적
        elif node_name == "agent" and hasattr(step, 'text') and callable(step.text):
            text = step.text()
            if text:
                if not self.showed_agent_header:
                    self.showed_agent_header = True
                    print("\nAI 응답: ", end="", flush=True)
                print(text, end="", flush=True)
    
    def chat(self, message: str, user_id: str = "default_user", thread_id: str = "default_thread",
             pregnancy_week: int = 0, stream: bool = True) -> Dict[str, Any]:
        """
        메시지를 전송하여 대화를 시작합니다.
        
        Args:
            message: 사용자 메시지
            user_id: 사용자 ID
            thread_id: 스레드 ID
            pregnancy_week: 임신 주차 (기본값: 0)
            stream: 스트리밍 모드 사용 여부
            
        Returns:
            대화 결과
        """
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "pregnancy_week": pregnancy_week,
            "recall_memories": []
        }
        
        config = {"configurable": {"user_id": user_id, "thread_id": thread_id}}
        
        # 상태 초기화 (메서드 속성이 아닌 클래스 인스턴스 속성 사용)
        self.initialized_output = False
        self.showed_agent_header = False
        self.showed_tools_header = False
        self.showed_tool_result = False
        
        if stream:
            # 스트리밍 모드
            result = {"response": ""}
            for step, metadata in self.agent_executor.stream(
                initial_state,
                stream_mode="messages",
                config=config
            ):
                self.clean_stream_output(step, metadata)
                
                # 텍스트 응답 누적
                if (metadata.get("langgraph_node") == "agent" and 
                    hasattr(step, 'text') and callable(step.text)):
                    result["response"] += step.text() or ""
                    
            print()  # 줄바꿈 추가
            return result
        else:
            # 일반 모드
            response = self.agent_executor.invoke(initial_state, config=config)
            # 마지막 메시지 추출
            final_message = response["messages"][-1].content if response["messages"] else ""
            return {"response": final_message}


# CLI 인터페이스
def main():
    """명령줄에서 실행할 때의 진입점"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Florence 임신정보 어시스턴트")
    parser.add_argument("--message", "-m", type=str, help="메시지 내용")
    parser.add_argument("--user-id", "-u", type=str, default="default_user", help="사용자 ID")
    parser.add_argument("--pregnancy-week", "-p", type=int, default=0, help="임신 주차")
    parser.add_argument("--no-stream", action="store_true", help="스트리밍 모드 비활성화")
    
    args = parser.parse_args()
    
    # Florence 인스턴스 생성
    florence = Florence()
    
    if args.message:
        # 명령줄 인자로 전달된 메시지로 대화
        florence.chat(
            message=args.message,
            user_id=args.user_id,
            pregnancy_week=args.pregnancy_week,
            stream=not args.no_stream
        )
    else:
        # 대화형 모드
        print("Florence 임신정보 어시스턴트와 대화를 시작합니다. 종료하려면 'exit' 또는 'quit'를 입력하세요.")
        user_id = input("사용자 ID를 입력하세요 (기본값: default_user): ") or "default_user"
        pregnancy_week = input("임신 주차를 입력하세요 (기본값: 0): ")
        pregnancy_week = int(pregnancy_week) if pregnancy_week.isdigit() else 0
        
        while True:
            message = input("\n> ")
            if message.lower() in ["exit", "quit", "종료"]:
                print("대화를 종료합니다.")
                break
                
            florence.chat(
                message=message,
                user_id=user_id,
                pregnancy_week=pregnancy_week,
                stream=not args.no_stream
            )


# 모듈로 임포트되었을 때와 직접 실행되었을 때를 구분
if __name__ == "__main__":
    main()
    
    
# 장고서버 utils.py파일에서 호출하는 함수
def chat_with_florence(message: str, user_id: str = "default_user", thread_id: str = "default_thread",
                       pregnancy_week: int = 0, stream: bool = True) -> Dict[str, Any]:
    florence = Florence()
    return florence.chat(message, user_id, thread_id, pregnancy_week, stream)