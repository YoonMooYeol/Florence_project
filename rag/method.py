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
    
    @staticmethod
    def process_file(file_path: str):
        """
        파일을 처리하여 벡터 DB에 저장합니다.
        
        Args:
            file_path: 처리할 파일 경로
            
        Returns:
            성공 여부(True/False)
        """
        print(f"파일 처리 중: {file_path}")
        
        # 파일 확장자 확인
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 파일 유형에 따라 적절한 로더 사용
        if file_ext == '.csv':
            # 1. CSV 파일 로드
            # CSVLoader는 csv 파일의 각 행을 별도의 문서(Document)로 변환합니다
            loader = CSVLoader(file_path=file_path)
            documents = loader.load()
            print(f"CSV 문서 로드 완료: {len(documents)}개 행")
        elif file_ext == '.txt':
            # 1. TXT 파일 로드
            # TextLoader는 텍스트 파일을 하나의 문서로 로드합니다
            loader = TextLoader(file_path=file_path, encoding='utf-8')
            documents = loader.load()
            print(f"TXT 문서 로드 완료: {len(documents)}개 문서")
        elif file_ext == '.json' or file_ext == '.jsonl':
            # JSON 또는 JSONL 파일 로드
            try:
                # 파일이 jsonlines 형식인지 확인
                is_jsonlines = file_ext == '.jsonl'
                
                if is_jsonlines:
                    # JSONL 파일 처리
                    try:
                        # 각 라인을 개별적으로 읽어서 처리
                        json_lines = []
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    try:
                                        item = json.loads(line)
                                        json_lines.append(item)
                                    except Exception as e:
                                        logger.warning(f"JSONL 라인 파싱 오류: {str(e)}")
                        
                        if not json_lines:
                            logger.error("유효한 JSON 객체를 포함한 라인이 없습니다.")
                            return False
                        
                        # 첫 번째 객체에서 텍스트 필드 찾기
                        sample_obj = json_lines[0]
                        text_fields = SimpleRAG._find_text_fields(sample_obj)
                        
                        if text_fields:
                            # 가장 긴 텍스트 필드 선택
                            best_path = max(text_fields.items(), key=lambda x: x[1])[0]
                            content_key = best_path.split('.')[-1]  # 경로에서 실제 키 추출
                            
                            # jq 호환 형식으로 경로 변환
                            jq_best_path = SimpleRAG._path_to_jq_schema(best_path)
                            
                            # 메타데이터로 사용할 필드 결정 (긴 텍스트 필드 제외)
                            def metadata_func(record, metadata):
                                extra_meta = SimpleRAG._extract_metadata(record, [best_path])
                                return {**metadata, **extra_meta}
                            
                            # JSONLoader 생성
                            loader = JSONLoader(
                                file_path=file_path,
                                jq_schema=jq_best_path,  # 변환된 경로 사용
                                text_content=False,  # 전체 콘텐츠 사용
                                json_lines=True,
                                metadata_func=metadata_func
                            )
                        else:
                            # 텍스트 필드가 없으면 전체 객체를 JSON으로 변환
                            loader = JSONLoader(
                                file_path=file_path,
                                jq_schema='.',
                                text_content=False,
                                json_lines=True
                            )
                    except Exception as e:
                        logger.error(f"JSONL 파일 처리 중 오류: {str(e)}")
                        return False
                else:
                    # 일반 JSON 파일 처리
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                        
                        # JSON 구조에서 텍스트 필드 찾기
                        text_fields = SimpleRAG._find_text_fields(json_data)
                        
                        if not text_fields:
                            # 텍스트 필드가 없는 경우 전체 JSON을 텍스트로 변환
                            logger.info("적절한 텍스트 필드를 찾지 못했습니다. 전체 JSON을 사용합니다.")
                            content = json.dumps(json_data, ensure_ascii=False)
                            documents = [Document(page_content=content, metadata={"source": file_path})]
                            print(f"JSON 문서 직접 변환 완료: {len(documents)}개 문서")
                            
                            # 이미 documents를 생성했으므로 loader를 가상으로 설정
                            class DummyLoader:
                                def load(self):
                                    return documents
                            
                            loader = DummyLoader()
                        else:
                            # 가장 긴 텍스트 필드 선택
                            best_path = max(text_fields.items(), key=lambda x: x[1])[0]
                            print(f"가장 긴 텍스트 필드 경로: {best_path}")
                            
                            # jq 호환 형식으로 경로 변환
                            jq_best_path = SimpleRAG._path_to_jq_schema(best_path)
                            
                            # 배열 처리가 필요한지 확인
                            if '[]' in best_path or '[0]' in best_path:
                                # 배열 형태의 JSON 처리
                                # [0]을 []로 변경하여 모든 요소 처리
                                jq_path = jq_best_path.replace('[0]', '[]')
                                
                                # 메타데이터 추출 설정
                                def metadata_func(record, metadata):
                                    # record는 jq_schema에 의해 추출된 객체
                                    extra_meta = {}
                                    if isinstance(record, dict):
                                        extra_meta = SimpleRAG._extract_metadata(record, [best_path])
                                    return {**metadata, **extra_meta}
                                
                                loader = JSONLoader(
                                    file_path=file_path,
                                    jq_schema=jq_path,
                                    text_content=False,
                                    metadata_func=metadata_func
                                )
                            else:
                                # 단일 필드 추출
                                # 메타데이터 생성 함수
                                def metadata_func(record, metadata):
                                    extra_meta = SimpleRAG._extract_metadata(json_data, [best_path])
                                    return {**metadata, **extra_meta}
                                
                                # jq_schema 설정
                                loader = JSONLoader(
                                    file_path=file_path,
                                    jq_schema=jq_best_path,  # 변환된 경로 사용
                                    text_content=False,
                                    metadata_func=metadata_func
                                )
                    except Exception as e:
                        logger.error(f"JSON 파일 처리 중 오류: {str(e)}")
                        return False
                
                # 문서 로드
                documents = loader.load()
                print(f"JSON 문서 로드 완료: {len(documents)}개 문서")
                
            except Exception as e:
                logger.error(f"JSON 파일 처리 중 오류 발생: {str(e)}")
                return False
        else:
            print(f"지원하지 않는 파일 형식: {file_ext}")
            return False
        
        # 2. 문서 분할
        # 긴 문서를 청크(chunk)로 나누어 임베딩하기 좋게 만듭니다
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # 각 청크의 최대 글자 수
            chunk_overlap=200,  # 청크 간 중복 글자 수
        )
        splits = text_splitter.split_documents(documents)
        print(f"문서 분할 완료: {len(splits)}개 청크")
        
        # 3. 청크에서 텍스트와 메타데이터 추출
        texts = [doc.page_content for doc in splits]
        metadatas = [doc.metadata for doc in splits]
        
        # 4. OpenAI 임베딩 모델 설정
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # 5. Chroma DB 업데이트 또는 생성
        if os.path.exists(SimpleRAG.DB_DIR):
            print("기존 Chroma DB 업데이트 중...")
            logger.info(f"기존 Chroma DB 경로: {SimpleRAG.DB_DIR}")
            # 기존 DB가 있으면 로드해서 업데이트
            vectorstore = Chroma(
                persist_directory=SimpleRAG.DB_DIR,
                embedding_function=embeddings,
                collection_name="korean_dialogue"
            )
            # 새 텍스트 추가
            logger.info(f"Chroma DB에 {len(texts)}개 텍스트 추가 중...")
            vectorstore.add_texts(texts=texts, metadatas=metadatas)
        else:
            print("새로운 Chroma DB 생성 중...")
            logger.info(f"새 Chroma DB 경로: {SimpleRAG.DB_DIR}")
            # 새 DB 생성
            try:
                logger.info("Chroma.from_texts() 호출 시작...")
                vectorstore = Chroma.from_texts(
                    texts=texts,
                    embedding_function=embeddings,
                    metadatas=metadatas,
                    persist_directory=SimpleRAG.DB_DIR,
                    collection_name="korean_dialogue"
                )
                logger.info("Chroma.from_texts() 호출 성공")
            except Exception as e:
                logger.error(f"Chroma DB 생성 중 오류: {str(e)}")
                # 매개변수 이름이 'embedding'일 경우 다시 시도
                try:
                    logger.info("매개변수 'embedding'으로 다시 시도...")
                    vectorstore = Chroma.from_texts(
                        texts=texts,
                        embedding=embeddings,
                        metadatas=metadatas,
                        persist_directory=SimpleRAG.DB_DIR,
                        collection_name="korean_dialogue"
                    )
                    logger.info("Chroma.from_texts() 두 번째 시도 성공")
                except Exception as e2:
                    logger.error(f"두 번째 시도 중 오류: {str(e2)}")
                    return False
        
        # 6. 변경사항 저장
        try:
            logger.info(f"Chroma DB 저장 디렉토리 생성: {SimpleRAG.DB_DIR}")
            os.makedirs(SimpleRAG.DB_DIR, exist_ok=True)
            
            # DB 디렉토리 권한 확인
            if not os.access(SimpleRAG.DB_DIR, os.W_OK):
                logger.error(f"Chroma DB 디렉토리에 쓰기 권한 없음: {SimpleRAG.DB_DIR}")
                raise PermissionError(f"디렉토리에 쓰기 권한 없음: {SimpleRAG.DB_DIR}")
            
            # 최신 버전의 langchain-chroma에서는 persist() 메서드가 필요하지 않음
            # 변경사항은 자동으로 저장됨
            logger.info("Chroma DB가 자동으로 저장됩니다. persist() 메서드는 더 이상 필요하지 않습니다.")
            
            # 저장 후 DB 폴더 내용 확인
            db_files = os.listdir(SimpleRAG.DB_DIR)
            logger.info(f"Chroma DB 저장 후 파일/폴더 목록: {db_files}")
            
            print("Chroma DB 저장 완료")
            return True
            
        except Exception as e:
            logger.error(f"Chroma DB 저장 중 오류 발생: {str(e)}")
            return False