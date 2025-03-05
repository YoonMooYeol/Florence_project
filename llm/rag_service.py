import os
import logging
from typing import Dict, Any, List, Optional

from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from django.conf import settings

from rag.method import SimpleRAG

# 로깅 설정
logger = logging.getLogger(__name__)

class RAGService:
    """
    RAG(Retrieval-Augmented Generation) 서비스 클래스
    
    이 클래스는 Chroma DB에 저장된 임베딩 데이터를 LangChain을 통해 로드하고,
    LLM과 결합하여 RAG 기반 질의응답을 수행합니다.
    """
    
    def __init__(self):
        """RAG 서비스 초기화"""
        self.db_dir = SimpleRAG.DB_DIR
        self.llm_model = os.getenv('LLM_MODEL', 'gpt-4')
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.chain = None
        self.vectorstore = None
        
    def initialize(self):
        """벡터 스토어 및 체인 초기화"""
        try:
            # Chroma DB가 존재하는지 확인
            if not os.path.exists(self.db_dir):
                logger.warning(f"벡터 DB 경로가 존재하지 않습니다: {self.db_dir}")
                return False
                
            # 벡터 스토어 로드
            self.vectorstore = Chroma(
                persist_directory=self.db_dir,
                embedding_function=self.embeddings,
                collection_name="korean_dialogue"
            )
            
            # 검색 도구 생성
            retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}  # 상위 3개 문서 검색
            )
            
            # 프롬프트 템플릿 정의
            qa_prompt = PromptTemplate.from_template("""
            당신은 임신과 출산에 대한 의학적으로 정확한 정보를 제공하는 전문가이자 질문자의 친구입니다. 
            항상 친절하고 명확하게 응답해주세요. 정확한 정보만 제공해야합니다. 사용자의 질문과 동일한 언어로 응답하세요.

            다음은 맥락 정보입니다:
            {context}

            다음은 사용자와의 이전 대화 내용입니다:
            {chat_history}

            사용자 질문: {question}
            """)
            
            # 대화 메모리 설정
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"  # 명시적으로 output_key 설정
            )
            
            # LLM 모델 설정
            llm = ChatOpenAI(temperature=0.3, model=self.llm_model)
            
            # 대화형 검색 체인 생성
            self.chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=retriever,
                memory=memory,
                return_source_documents=True,
                combine_docs_chain_kwargs={"prompt": qa_prompt},
                verbose=True
            )
            
            logger.info("RAG 서비스가 성공적으로 초기화되었습니다.")
            return True
            
        except Exception as e:
            logger.error(f"RAG 서비스 초기화 중 오류 발생: {str(e)}")
            return False
    
    def query(self, query_text: str, user_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        RAG 기반 질의응답 수행
        
        Args:
            query_text: 사용자 질문
            user_info: 사용자 정보 (선택)
            
        Returns:
            dict: 응답 및 참조 문서
        """
        # 서비스 초기화 확인
        if not self.chain:
            success = self.initialize()
            if not success:
                return {
                    "response": "죄송합니다. RAG 서비스를 초기화할 수 없습니다. 일반 LLM으로 응답합니다.",
                    "source_documents": [],
                    "using_rag": False
                }
        
        # 사용자 컨텍스트 추가
        enhanced_query = query_text
        if user_info:
            context = []
            if user_info.get('name'):
                context.append(f"사용자 이름: {user_info['name']}")
            if user_info.get('is_pregnant'):
                context.append("사용자는 임신 중입니다.")
            if user_info.get('pregnancy_week'):
                context.append(f"임신 {user_info['pregnancy_week']}주차입니다.")
            
            if context:
                context_str = "\n".join(context)
                enhanced_query = f"{context_str}\n\n{query_text}"
        
        try:
            # RAG 질의응답 수행
            result = self.chain({"question": enhanced_query})
            
            # 응답 및 출처 문서 추출
            response_text = result['answer']
            source_documents = []
            
            # 출처 문서 정보 추출
            if 'source_documents' in result:
                for i, doc in enumerate(result['source_documents']):
                    source = {
                        "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
                        "metadata": doc.metadata
                    }
                    source_documents.append(source)
            
            return {
                "response": response_text,
                "source_documents": source_documents,
                "using_rag": True
            }
            
        except Exception as e:
            logger.error(f"RAG 질의응답 중 오류 발생: {str(e)}")
            return {
                "response": "죄송합니다. RAG 서비스를 사용하는 중에 오류가 발생했습니다.",
                "source_documents": [],
                "using_rag": False
            }

# 싱글톤 인스턴스 생성
rag_service = RAGService() 