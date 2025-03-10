import os
from django.conf import settings
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import CSVLoader, TextLoader, JSONLoader
from langchain_chroma import Chroma
from langchain.schema import Document
from dotenv import load_dotenv
import json
import logging
import pandas as pd

# 로깅 설정
logger = logging.getLogger(__name__)
# 로그 레벨을 INFO로 설정하고 콘솔 핸들러 추가
if not logger.handlers:
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

load_dotenv()

class SimpleRAG:
    """
    간단한 임베딩 시스템 클래스
    
    이 클래스는 CSV, TXT, JSON 파일을 임베딩하여 벡터 DB에 저장하는 
    기능을 제공합니다.
    """
    # 벡터 DB가 저장될 경로
    DB_DIR = os.path.join(settings.BASE_DIR, "embeddings", "chroma_db")
    
    def __init__(self, persist_directory='./rag/chroma', rag_chroma=None, embeddings=None):
        # Initialize any other necessary attributes
        pass
    
    @staticmethod
    def _find_text_fields(json_obj, min_length=50, path="", results=None):
        """
        JSON 구조에서 텍스트 필드를 재귀적으로 찾습니다.
        
        Args:
            json_obj: 분석할 JSON 객체
            min_length: 텍스트로 간주할 최소 길이
            path: 현재 경로 (재귀 호출용)
            results: 누적 결과 (재귀 호출용)
            
        Returns:
            dict: 텍스트 필드의 jq 경로와 해당 필드의 길이를 매핑한 딕셔너리
        """
        if results is None:
            results = {}
            
        if isinstance(json_obj, dict):
            for key, value in json_obj.items():
                # 현재 경로 구성
                current_path = f"{path}.{key}" if path else f".{key}"
                
                if isinstance(value, str) and len(value) >= min_length:
                    # 긴 텍스트 필드 발견
                    results[current_path] = len(value)
                elif isinstance(value, (dict, list)):
                    # 중첩된 객체/배열 재귀 탐색
                    SimpleRAG._find_text_fields(value, min_length, current_path, results)
        
        elif isinstance(json_obj, list) and json_obj:
            # 리스트의 첫 번째 항목 분석 (샘플로)
            if isinstance(json_obj[0], dict):
                # 객체 배열인 경우 첫 번째 항목을 분석
                first_path = f"{path}[0]" if path else "[0]"
                SimpleRAG._find_text_fields(json_obj[0], min_length, first_path, results)
            elif isinstance(json_obj[0], str) and len(json_obj[0]) >= min_length:
                # 텍스트 배열인 경우
                list_path = f"{path}[]" if path else "[]"
                results[list_path] = len(json_obj[0])
                
        return results
    
    @staticmethod
    def _extract_metadata(json_obj, exclude_paths=None, path="", metadata=None, max_string_length=100):
        """
        JSON 객체에서 메타데이터로 적합한 필드를 추출합니다.
        
        Args:
            json_obj: 메타데이터를 추출할 JSON 객체
            exclude_paths: 제외할 경로 목록
            path: 현재 경로 (재귀 호출용)
            metadata: 누적 메타데이터 (재귀 호출용)
            max_string_length: 메타데이터로 추출할 문자열의 최대 길이
            
        Returns:
            dict: 추출된 메타데이터
        """
        if metadata is None:
            metadata = {}
            
        if exclude_paths is None:
            exclude_paths = []
            
        if isinstance(json_obj, dict):
            for key, value in json_obj.items():
                # 현재 경로 구성
                current_path = f"{path}.{key}" if path else f".{key}"
                
                # 제외 경로에 포함되지 않는 필드만 처리
                if current_path not in exclude_paths:
                    if isinstance(value, (int, float, bool)):
                        # 기본 타입은 메타데이터로 추가
                        flat_key = key if not path else f"{path.lstrip('.')}.{key}"
                        metadata[flat_key] = value
                    elif isinstance(value, str) and len(value) <= max_string_length:
                        # 짧은 문자열만 메타데이터로 추가
                        flat_key = key if not path else f"{path.lstrip('.')}.{key}"
                        metadata[flat_key] = value
                    elif isinstance(value, (dict, list)) and not any(current_path.startswith(p) for p in exclude_paths):
                        # 중첩된 객체/배열에 대해 재귀 호출 (제외 경로에 포함되지 않는 경우)
                        SimpleRAG._extract_metadata(value, exclude_paths, current_path, metadata, max_string_length)
        
        elif isinstance(json_obj, list) and len(json_obj) <= 5:  # 짧은 리스트만 처리
            for i, item in enumerate(json_obj):
                if isinstance(item, (int, float, bool, str)) and (not isinstance(item, str) or len(item) <= max_string_length):
                    # 기본 타입 배열 항목을 메타데이터로 추가
                    flat_key = f"{path.lstrip('.')}[{i}]" if path else f"[{i}]"
                    metadata[flat_key] = item
                    
        return metadata
    
    @staticmethod
    def _path_to_jq_schema(path):
        """
        경로를 jq 호환 형식으로 변환합니다.
        한글 필드명을 포함한 경로를 .["필드명"] 형식으로 변환합니다.
        
        Args:
            path: 변환할 경로 (예: .임신_17주차.임산부_변화.심리적_변화)
            
        Returns:
            jq 호환 형식의 경로 (예: .["임신_17주차"]["임산부_변화"]["심리적_변화"])
        """
        if not path:
            return path
            
        result = ""
        parts = path.split('.')
        
        for part in parts:
            if not part:  # 빈 부분 건너뛰기 (시작이 .인 경우)
                result += "."
                continue
                
            # 배열 인덱스 처리 ([0], [], 등)
            if '[' in part and ']' in part:
                array_part = part.split('[', 1)
                field_name = array_part[0]
                array_suffix = '[' + array_part[1]
                
                # 필드명이 있는 경우에만 ["필드명"] 형식으로 변환
                if field_name:
                    result += f'["{field_name}"]'
                
                # 배열 부분 그대로 추가
                result += array_suffix
            else:
                # 일반 필드는 ["필드명"] 형식으로 변환
                result += f'["{part}"]'
                
        logger.info(f"경로 변환: {path} -> {result}")
        return result
    
    def process_file(self, file_path):
        """파일을 처리하여 문서로 변환"""
        # CSV 파일 특별 처리
        if file_path.endswith('.csv'):
            import pandas as pd
            
            # CSV 파일 로드
            df = pd.read_csv(file_path)
            documents = []
            
            logger.info(f"CSV 파일 처리 시작: {file_path}, 컬럼: {df.columns.tolist()}")
            
            # 각 행을 문서로 변환
            for idx, row in df.iterrows():
                # 임신 주차 확인 (여러 가능한 컬럼명 시도)
                pregnancy_week = None
                pregnancy_week_columns = ['임신주차', '임신 주차', '주차', 'week', 'pregnancy_week']
                
                for col in pregnancy_week_columns:
                    if col in df.columns:
                        try:
                            value = row[col]
                            if pd.notna(value):  # NaN이 아닌 경우만 처리
                                # 문자열인 경우 정수로 변환 시도
                                if isinstance(value, str):
                                    # 숫자만 추출 (예: "8주차" -> "8")
                                    import re
                                    num_match = re.search(r'(\d+)', value)
                                    if num_match:
                                        pregnancy_week = int(num_match.group(1))
                                else:
                                    pregnancy_week = int(value)
                                break
                        except:
                            continue
                
                # 첫 번째 컬럼이 숫자이고 임신주차를 찾지 못한 경우, 첫 번째 컬럼을 임신주차로 가정
                if pregnancy_week is None and len(df.columns) > 0:
                    first_col = df.columns[0]
                    try:
                        value = row[first_col]
                        if pd.notna(value):
                            if isinstance(value, str):
                                import re
                                num_match = re.search(r'(\d+)', value)
                                if num_match:
                                    pregnancy_week = int(num_match.group(1))
                            else:
                                pregnancy_week = int(value)
                    except:
                        pass
                
                logger.info(f"행 {idx} 처리: 임신주차={pregnancy_week}")
                        
                # 콘텐츠 생성 - 임신 주차를 첫 줄에 명확히 표시
                if pregnancy_week is not None:
                    content = f"임신주차: {pregnancy_week}\n"
                    content += "\n".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val) and col != '임신주차'])
                else:
                    content = "\n".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
                    
                # 메타데이터에 임신 주차 정보 추가
                metadata = {
                    "source": file_path,
                    "row": idx
                }
                
                # 임신 주차 정보가 있으면 메타데이터에 추가 (다양한 키로 저장)
                if pregnancy_week is not None:
                    metadata["pregnancy_week"] = pregnancy_week
                    metadata["임신주차"] = pregnancy_week
                    metadata["week"] = pregnancy_week
                    metadata["주차"] = pregnancy_week
                    
                documents.append(Document(page_content=content, metadata=metadata))
            
            logger.info(f"CSV 파일 처리 완료: {file_path}, {len(documents)}개 문서 생성")
            return documents
        
        # 다른 파일 형식 처리 코드...

    @staticmethod
    def search_by_pregnancy_week(query: str, pregnancy_week: int, k: int = 3):
        """
        임신 주차를 기준으로 관련 정보를 검색합니다.
        
        Args:
            query: 검색 쿼리
            pregnancy_week: 임신 주차
            k: 반환할 문서 수
            
        Returns:
            관련 문서 목록
        """
        try:
            # OpenAI 임베딩 모델 설정
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            
            # Chroma DB 로드
            vectorstore = Chroma(
                persist_directory=SimpleRAG.DB_DIR,
                embedding_function=embeddings,
                collection_name="korean_dialogue"
            )
            
            # 1. 임신 주차로 필터링된 검색 시도
            filter_dict = {"pregnancy_week": pregnancy_week}
            try:
                # 임신 주차로 필터링하여 검색
                results = vectorstore.similarity_search(
                    query, 
                    k=k,
                    filter=filter_dict
                )
                
                # 결과가 있으면 반환
                if results:
                    logger.info(f"임신 {pregnancy_week}주차로 필터링된 검색 결과: {len(results)}개")
                    return results
            except Exception as e:
                logger.warning(f"임신 주차 필터링 검색 오류: {str(e)}")
            
            # 2. 쿼리 확장 방식 시도
            expanded_query = f"임신 {pregnancy_week}주차 {query}"
            logger.info(f"확장된 쿼리: {expanded_query}")
            
            # 확장된 쿼리로 검색
            results = vectorstore.similarity_search(expanded_query, k=k)
            
            # 3. 결과 후처리: 임신 주차와 가까운 순으로 정렬
            if results:
                # 메타데이터에 임신 주차 정보가 있는 경우 주차 차이에 따라 정렬
                def get_week_difference(doc):
                    doc_week = doc.metadata.get('pregnancy_week')
                    if doc_week is not None:
                        return abs(doc_week - pregnancy_week)
                    return 100  # 임신 주차 정보가 없는 경우 높은 값 반환
                
                # 임신 주차 차이가 적은 순으로 정렬
                results.sort(key=get_week_difference)
                
                # 상위 k개 결과만 반환
                return results[:k]
            
            return results
            
        except Exception as e:
            logger.error(f"임신 주차 기반 검색 중 오류: {str(e)}")
            # 오류 발생 시 빈 결과 반환
            return []