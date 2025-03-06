import os
import logging
import re
import json
from typing import Dict, Any, List, Optional

from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from django.conf import settings
from accounts.models import Pregnancy  # Pregnancy 모델 임포트

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
        self.llm_model = os.getenv('LLM_MODEL', 'gpt-4o')
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
            당신은 임신과 출산에 대한 의학적으로 정확한 정보를 제공하는 질문자의 친구입니다. 
            항상 친구처럼 친근하게 응답해주세요. 정확한 정보만 제공해야합니다. 사용자의 질문과 동일한 언어로 응답하세요.

            다음은 맥락 정보입니다:
            {context}

            다음은 사용자와의 이전 대화 내용입니다:
            {chat_history}

            사용자 정보와 질문: {question}
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
    
    def query(self, query_text, user_context=None):
        """
        RAG 서비스를 사용하여 질의에 응답합니다.
        
        Args:
            query_text: 사용자 질의
            user_context: 사용자 컨텍스트 정보
            
        Returns:
            응답 텍스트와 소스 문서 정보
        """
        try:
            # 임신 관련 키워드
            pregnancy_keywords = ["임신", "출산", "태아", "주차", "개월", "입덧", "양수", "태동", "진통", "분만", "산모", "임산부", "먹어야", "음식", "영양", "건강"]
            
            # 임신 주차 패턴
            pregnancy_week_patterns = [
                r'임신\s*(\d+)\s*주차',  # "임신 8주차"
                r'(\d+)\s*주차\s*임신',  # "8주차 임신"
                r'(\d+)\s*주\s*임신',    # "8주 임신"
                r'임신\s*(\d+)\s*주',    # "임신 8주"
            ]
            
            # 임신 주차 추출
            pregnancy_week = None
            for pattern in pregnancy_week_patterns:
                match = re.search(pattern, query_text)
                if match:
                    try:
                        pregnancy_week = int(match.group(1))
                        logger.info(f"임신 주차 감지: {pregnancy_week}주차")
                        break
                    except:
                        pass
            
            # 사용자 컨텍스트에서 임신 주차 확인
            if pregnancy_week is None and user_context and "pregnancy_week" in user_context:
                try:
                    pregnancy_week = int(user_context["pregnancy_week"])
                    logger.info(f"사용자 컨텍스트에서 임신 주차 확인: {pregnancy_week}주차")
                except:
                    pass
            
            logger.info(f"쿼리: '{query_text}', 임신 주차: {pregnancy_week}, 키워드 매치: {any(keyword in query_text for keyword in pregnancy_keywords)}")
            
            # 임신 관련 키워드가 있고 임신 주차 정보가 있는 경우
            if pregnancy_week is not None and any(keyword in query_text for keyword in pregnancy_keywords):
                logger.info(f"임신 {pregnancy_week}주차 관련 검색 시도")
                
                # 임신 주차 기반 검색
                documents = query_by_pregnancy_week(query_text, pregnancy_week)
                
                # 검색 결과가 있는 경우
                if documents:
                    logger.info(f"임신 {pregnancy_week}주차 관련 문서 {len(documents)}개 찾음")
                    for i, doc in enumerate(documents[:3]):
                        logger.info(f"문서 {i+1} 미리보기: {doc.page_content[:150]}...")
                        logger.info(f"문서 {i+1} 메타데이터: {json.dumps(doc.metadata, ensure_ascii=False)}")
                    
                    # 응답 생성
                    response_text = self._generate_response_from_docs(documents, query_text)
                    
                    # 소스 문서 정보 생성
                    source_documents = []
                    for doc in documents:
                        source_documents.append({
                            "content": doc.page_content,
                            "metadata": doc.metadata
                        })
                    
                    logger.info(f"소스 문서 수: {len(source_documents)}")
                    
                    result = {
                        "response": response_text,
                        "source_documents": source_documents,
                        "using_rag": True
                    }
                    
                    logger.info(f"임신 주차 검색 결과: {json.dumps(result, ensure_ascii=False)[:200]}...")
                    return result
            
            # 일반 RAG 검색
            logger.info("일반 RAG 검색 실행")
            
            # 벡터 저장소 로드
            embeddings = OpenAIEmbeddings()
            vectorstore = Chroma(
                persist_directory=SimpleRAG.DB_DIR,
                embedding_function=embeddings,
                collection_name="korean_dialogue"
            )
            
            # 벡터 저장소 상태 확인
            try:
                collection_data = vectorstore.get()
                total_docs = len(collection_data['ids'])
                logger.info(f"벡터 저장소 상태: 총 {total_docs}개 문서")
            except Exception as e:
                logger.warning(f"벡터 저장소 상태 확인 실패: {str(e)}")
            
            # 유사도 검색
            documents = vectorstore.similarity_search(query_text, k=3)
            logger.info(f"일반 검색 결과: {len(documents)}개 문서")
            
            # 응답 생성
            response_text = self._generate_response_from_docs(documents, query_text)
            
            # 소스 문서 정보 생성
            source_documents = []
            for doc in documents:
                source_documents.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })
            
            logger.info(f"소스 문서 수: {len(source_documents)}")
            
            result = {
                "response": response_text,
                "source_documents": source_documents,
                "using_rag": True
            }
            
            logger.info(f"일반 검색 결과: {json.dumps(result, ensure_ascii=False)[:200]}...")
            return result
            
        except Exception as e:
            logger.error(f"RAG 질의응답 중 오류 발생: {str(e)}")
            logger.exception("상세 오류:")
            return {
                "response": "죄송합니다. RAG 서비스를 사용하는 중에 오류가 발생했습니다.",
                "source_documents": [],
                "using_rag": False
            }

    def _generate_response_from_docs(self, documents, query_text):
        """문서를 기반으로 응답 생성"""
        # LLM 설정
        llm = ChatOpenAI(model=self.llm_model, temperature=0.3)
        
        # 문서 내용 결합
        context = "\n\n".join([doc.page_content for doc in documents])
        
        # 프롬프트 구성
        prompt = f"""
        You are a friendly companion providing medically accurate information about pregnancy and childbirth.  
        Always respond warmly. Answer questions within 80~100 characters accurately.  
        If the topic is unrelated to pregnancy, please ask a question related to pregnancy. and Respond strictly in Korean.  

        Here is the pregnancy week information:  
        {context}  

        User’s info & question: {query_text}  

        Based on the above context, kindly respond to the user’s question.  
        If the information is insufficient, honestly say you don’t know.  
        """
        
        # 응답 생성
        response = llm.invoke(prompt)
        return response.content

# 싱글톤 인스턴스 생성
rag_service = RAGService() 

def query_by_pregnancy_week(query, pregnancy_week):
    """임신 주차에 맞는 정보를 검색합니다."""
    import re  # 정규 표현식 모듈 임포트 추가
    
    logger.info(f"임신 주차 검색 시작: 주차={pregnancy_week}, 쿼리='{query}'")
    
    # 벡터 저장소 로드
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(
        persist_directory=SimpleRAG.DB_DIR,
        embedding_function=embeddings,
        collection_name="korean_dialogue"
    )
    
    # 0. 벡터 저장소 상태 확인
    try:
        collection_data = vectorstore.get()
        total_docs = len(collection_data['ids'])
        logger.info(f"벡터 저장소 상태: 총 {total_docs}개 문서")
        
        # 메타데이터 확인
        if 'metadatas' in collection_data and collection_data['metadatas']:
            meta_samples = collection_data['metadatas'][:5]
            logger.info(f"메타데이터 샘플: {json.dumps(meta_samples, ensure_ascii=False)}")
            
            # 특정 임신 주차 확인
            if pregnancy_week:
                week_found = False
                for meta in collection_data['metadatas']:
                    for key in ["pregnancy_week", "week", "임신주차", "주차"]:
                        if key in meta and meta[key] is not None:
                            try:
                                if isinstance(meta[key], (int, float)) and int(meta[key]) == pregnancy_week:
                                    week_found = True
                                    logger.info(f"임신 {pregnancy_week}주차 메타데이터 확인됨")
                                    break
                                elif isinstance(meta[key], str) and meta[key].isdigit() and int(meta[key]) == pregnancy_week:
                                    week_found = True
                                    logger.info(f"임신 {pregnancy_week}주차 메타데이터 확인됨 (문자열)")
                                    break
                            except:
                                pass
                    if week_found:
                        break
                
                if not week_found:
                    logger.warning(f"임신 {pregnancy_week}주차에 해당하는 메타데이터를 찾을 수 없음")
    except Exception as e:
        logger.warning(f"벡터 저장소 상태 확인 실패: {str(e)}")
    
    # 1. 모든 가능한 메타데이터 필터 형식 시도
    filter_attempts = [
        {"pregnancy_week": pregnancy_week},
        {"pregnancy_week": str(pregnancy_week)},
        {"임신주차": pregnancy_week},
        {"임신주차": str(pregnancy_week)},
        {"week": pregnancy_week},
        {"week": str(pregnancy_week)},
        {"주차": pregnancy_week},
        {"주차": str(pregnancy_week)}
    ]
    
    logger.info(f"메타데이터 필터 시도: {filter_attempts}")
    
    # 각 필터 시도
    for filter_dict in filter_attempts:
        try:
            logger.info(f"필터 시도: {filter_dict}")
            exact_results = vectorstore.similarity_search(
                query, 
                k=5,
                filter=filter_dict
            )
            if exact_results:
                logger.info(f"메타데이터 필터링 성공: {filter_dict}, 결과 수: {len(exact_results)}")
                for i, doc in enumerate(exact_results[:3]):
                    logger.info(f"메타데이터 필터링 결과 {i+1}: {doc.page_content[:150]}")
                    logger.info(f"메타데이터: {json.dumps(doc.metadata, ensure_ascii=False)}")
                # 정확히 일치하는 결과만 반환
                return exact_results
        except Exception as e:
            logger.warning(f"메타데이터 필터 오류: {filter_dict}, 오류: {str(e)}")
    
    # 2. 명시적 주차 포함 쿼리 실행
    logger.info("메타데이터 필터링 실패, 내용 기반 검색 시도")
    
    # 다양한 형태의 확장 쿼리 시도
    expanded_queries = [
        f"임신 {pregnancy_week}주차 {query}",
        f"임신주차 {pregnancy_week} {query}",
        f"{pregnancy_week}주차 임신 {query}",
        f"{pregnancy_week}주 {query}"
    ]
    
    # 확장 쿼리로 검색
    all_results = []
    for expanded_query in expanded_queries:
        logger.info(f"확장 쿼리 시도: '{expanded_query}'")
        try:
            results = vectorstore.similarity_search(expanded_query, k=5)
            logger.info(f"확장 쿼리 결과 수: {len(results)}")
            all_results.extend(results)
        except Exception as e:
            logger.warning(f"확장 쿼리 오류: {expanded_query}, 오류: {str(e)}")
    
    # 중복 제거
    seen_ids = set()
    unique_results = []
    for doc in all_results:
        doc_id = doc.page_content  # 내용 기반으로 중복 체크
        if doc_id not in seen_ids:
            seen_ids.add(doc_id)
            unique_results.append(doc)
    
    logger.info(f"중복 제거 후 결과 수: {len(unique_results)}")
    
    # 3. 임신 주차 추출 및 필터링 함수
    def extract_pregnancy_week(content):
        """문서 내용에서 임신 주차 추출"""
        patterns = [
            r'임신주차:\s*(\d+)',  # "임신주차: 8" 형식
            r'^임신주차[,\s]*(\d+)',  # "임신주차, 8" 형식
            r'^(\d+)[,\s]',  # "8, ..." 형식 (CSV 첫 열)
            r'임신\s*(\d+)\s*주차',  # "임신 8주차" 형식
            r'(\d+)\s*주차\s*임신',  # "8주차 임신" 형식
            r'(\d+)\s*주\s*임신',    # "8주 임신" 형식
            r'^(\d+),',  # CSV 첫 번째 열 (주차)
            r'주차:\s*(\d+)',  # "주차: 8" 형식
            r'임신주차\s*(\d+)',  # "임신주차 8" 형식
            r'(\d+)주차',  # "8주차" 형식
            r'(\d+)주',    # "8주" 형식
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, content, re.MULTILINE)
            if matches:
                try:
                    week = int(matches.group(1))
                    logger.info(f"문서에서 임신 {week}주차 정보 추출: 패턴='{pattern}'")
                    return week
                except:
                    pass
        return None
    
    # 4. 정확한 주차 필터링 - 주차가 일치하는 문서만 선택
    filtered_results = []
    for doc in unique_results:
        # 메타데이터에서 주차 확인
        meta_week = None
        for key in ["pregnancy_week", "week", "임신주차", "주차"]:
            if key in doc.metadata and doc.metadata[key] is not None:
                try:
                    if isinstance(doc.metadata[key], (int, float)):
                        meta_week = int(doc.metadata[key])
                        break
                    elif isinstance(doc.metadata[key], str) and doc.metadata[key].isdigit():
                        meta_week = int(doc.metadata[key])
                        break
                except:
                    pass
        
        if meta_week == pregnancy_week:
            filtered_results.append(doc)
            logger.info(f"메타데이터에서 임신 {pregnancy_week}주차 정보 발견: {doc.page_content[:150]}")
            continue
            
        # 내용에서 주차 추출
        content_week = extract_pregnancy_week(doc.page_content)
        if content_week == pregnancy_week:
            filtered_results.append(doc)
            logger.info(f"문서 내용에서 임신 {pregnancy_week}주차 정보 발견: {doc.page_content[:150]}")
    
    # 5. 필터링된 결과가 있으면 반환
    if filtered_results:
        logger.info(f"임신 {pregnancy_week}주차 필터링 결과: {len(filtered_results)}개")
        for i, doc in enumerate(filtered_results[:3]):
            logger.info(f"필터링 결과 {i+1}: {doc.page_content[:150]}")
            # 메타데이터 확인
            logger.info(f"필터링 결과 {i+1} 메타데이터: {json.dumps(doc.metadata, ensure_ascii=False)}")
        return filtered_results[:5]
    
    # 6. 필터링된 결과가 없으면 유사도 기반 접근
    logger.info("정확한 주차 필터링 실패, 유사도 기반 접근 시도")
    
    # 유사도 계산 함수
    def get_pregnancy_week_similarity(doc):
        # 메타데이터에서 주차 확인
        meta_week = None
        for key in ["pregnancy_week", "week", "임신주차", "주차"]:
            if key in doc.metadata and doc.metadata[key] is not None:
                try:
                    if isinstance(doc.metadata[key], (int, float)):
                        meta_week = int(doc.metadata[key])
                        break
                    elif isinstance(doc.metadata[key], str) and doc.metadata[key].isdigit():
                        meta_week = int(doc.metadata[key])
                        break
                except:
                    pass
                    
        if meta_week is not None:
            similarity = 1.0 / (1 + abs(meta_week - pregnancy_week))
            return similarity
            
        # 내용에서 주차 추출
        content_week = extract_pregnancy_week(doc.page_content)
        if content_week is not None:
            similarity = 1.0 / (1 + abs(content_week - pregnancy_week))
            return similarity
            
        return 0  # 주차 정보 없음
    
    # 적어도 최소한의 결과를 확보하기 위해 기본 검색 수행
    try:
        # 임신 관련 키워드로 확장된 검색
        base_query = f"임신 주차 {query}"
        basic_results = vectorstore.similarity_search(base_query, k=20)
        logger.info(f"기본 검색 결과 수: {len(basic_results)}")
        
        # 거의 모든 문서를 가져와 필터링하는 방식 시도
        if not basic_results or len(basic_results) < 3:
            all_docs_query = "임신 태아 산모"
            basic_results = vectorstore.similarity_search(all_docs_query, k=50)
            logger.info(f"전체 문서 검색 결과 수: {len(basic_results)}")
    except Exception as e:
        logger.warning(f"기본 검색 오류: {str(e)}")
        basic_results = []
    
    # 주차 유사도로 정렬
    basic_results.sort(key=get_pregnancy_week_similarity, reverse=True)
    
    # 디버깅 정보
    for i, doc in enumerate(basic_results[:5]):
        content_week = extract_pregnancy_week(doc.page_content)
        meta_week = None
        for key in ["pregnancy_week", "week", "임신주차", "주차"]:
            if key in doc.metadata and doc.metadata[key] is not None:
                try:
                    meta_week = doc.metadata[key]
                    break
                except:
                    pass
        
        logger.info(f"결과 {i+1} - 내용 주차: {content_week}, 메타데이터 주차: {meta_week}")
        logger.info(f"미리보기: {doc.page_content[:150]}...")
        # 메타데이터 확인
        logger.info(f"결과 {i+1} 메타데이터: {json.dumps(doc.metadata, ensure_ascii=False)}")
    
    # 아무 것도 못 찾은 경우 - 유사도와 상관없이 일반 검색 결과 반환
    if not basic_results:
        logger.warning("임신 주차 기반 검색 실패, 일반 검색 결과 사용")
        try:
            default_results = vectorstore.similarity_search(query, k=5)
            logger.info(f"일반 검색 결과 수: {len(default_results)}")
            return default_results
        except Exception as e:
            logger.error(f"일반 검색 오류: {str(e)}")
            return []
    
    # 상위 5개 결과 반환
    top_results = basic_results[:5]
    logger.info(f"최종 반환 결과 수: {len(top_results)}")
    return top_results 