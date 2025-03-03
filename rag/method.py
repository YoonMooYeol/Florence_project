import os
from django.conf import settings
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import CSVLoader
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()

class SimpleRAG:
    """
    간단한 임베딩 시스템 클래스
    
    이 클래스는 CSV 파일을 임베딩하여 벡터 DB에 저장하는 
    기능을 제공합니다.
    """
    # 벡터 DB가 저장될 경로
    DB_DIR = os.path.join(settings.BASE_DIR, "embeddings", "chroma_db")
    
    @staticmethod
    def process_file(file_path: str):
        """
        CSV 파일을 처리하여 벡터 DB에 저장합니다.
        
        Args:
            file_path: 처리할 CSV 파일 경로
            
        Returns:
            성공 여부(True/False)
        """
        print(f"파일 처리 중: {file_path}")
        
        # 1. CSV 파일 로드
        # CSVLoader는 csv 파일의 각 행을 별도의 문서(Document)로 변환합니다
        loader = CSVLoader(file_path=file_path)
        documents = loader.load()
        print(f"문서 로드 완료: {len(documents)}개 행")
        
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
            # 기존 DB가 있으면 로드해서 업데이트
            vectorstore = Chroma(
                persist_directory=SimpleRAG.DB_DIR,
                embedding_function=embeddings,
                collection_name="korean_dialogue"
            )
            # 새 텍스트 추가
            vectorstore.add_texts(texts=texts, metadatas=metadatas)
        else:
            print("새로운 Chroma DB 생성 중...")
            # 새 DB 생성
            vectorstore = Chroma.from_texts(
                texts=texts,
                embedding=embeddings,
                metadatas=metadatas,
                persist_directory=SimpleRAG.DB_DIR,
                collection_name="korean_dialogue"
            )
        
        # 6. 변경사항 저장
        vectorstore.persist()
        print("Chroma DB 저장 완료")
        return True