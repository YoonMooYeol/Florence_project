from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings.openai import OpenAIEmbeddings
from langchain_community.chat_models import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import CSVLoader
import os
from glob import glob
import uuid
import pickle
from .models import RAG_DB
import asyncio
from typing import List
from langchain.prompts import ChatPromptTemplate
from django.conf import settings
from tqdm import tqdm

from dotenv import load_dotenv

load_dotenv()

class RAGProcessor:
    TEMP_DIR = "data/temp_embeddings"
    DB_DIR = os.path.join(settings.BASE_DIR, "embeddings", "chroma_db")

    @staticmethod
    def load_and_preprocess_csv(csv_pattern):
        """CSV 파일들을 찾아서 반환."""
        csv_files = glob(csv_pattern)
        if not csv_files:
            print(f"CSV 파일을 찾을 수 없습니다: {csv_pattern}")
            return None
        print(f"처리할 CSV 파일: {len(csv_files)}개")
        for file in csv_files:
            print(f"- {file}")
        return csv_files

    @staticmethod
    def filter_processed_files(csv_files):
        """이미 처리된 파일을 제외하고 새로운 파일 목록만 반환."""
        processed_files = set(RAG_DB.objects.values_list('file_path', flat=True))
        new_files = [f for f in csv_files if f not in processed_files]
        print(f"처리할 새로운 CSV 파일: {len(new_files)}개")
        return new_files

    @staticmethod
    def initialize_chroma_db():
        """Chroma DB를 초기화하거나 기존 DB를 로드."""
        db_dir = RAGProcessor.DB_DIR
        print("\n=== Chroma DB 상태 ===")
        print(f"사용 중인 DB 경로: {db_dir}")
        print(f"절대 경로: {os.path.abspath(db_dir)}")
        
        # DB 파일 존재 여부 확인
        if os.path.exists(f"{db_dir}/chroma.sqlite3"):
            print(f"chroma.sqlite3 파일 크기: {os.path.getsize(f'{db_dir}/chroma.sqlite3')} bytes")
        
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small", chunk_size=1000)

        if os.path.exists(db_dir) and os.path.exists(f"{db_dir}/chroma.sqlite3"):
            print("기존 Chroma DB 로드 중...")
            vectorstore = Chroma(
                persist_directory=db_dir,
                embedding_function=embeddings,
                collection_name="korean_dialogue"
            )
            existing_ids = set(vectorstore._collection.get()['ids'])
            print(f"기존 문서 수: {len(existing_ids)}")
        else:
            print("새로운 Chroma DB 생성")
            vectorstore = None
            existing_ids = set()

        return vectorstore, existing_ids

    @staticmethod
    def load_csv_with_metadata(csv_file):
        """CSV 파일을 로드하고 메타데이터 열을 추가."""
        print(f"\n파일 처리 중: {csv_file}")
        loader = CSVLoader(file_path=csv_file, metadata_columns=['emotion'])
        return loader.load()

    @staticmethod
    def filter_new_documents(docs, existing_ids, csv_file):
        """이미 존재하는 문서를 제외하고 새 문서만 필터링."""
        new_docs = []
        for idx, doc in enumerate(docs):
            doc.metadata['source_file'] = os.path.basename(csv_file)
            unique_id = str(uuid.uuid4())
            doc_id = f"doc_{unique_id}_{idx}"
            if doc_id not in existing_ids:
                doc.metadata['doc_id'] = doc_id
                new_docs.append(doc)
        print(f"새로운 문서 발견: {len(new_docs)}개")
        return new_docs

    @staticmethod
    def split_documents(docs):
        """문서를 청크로 분할."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        splits = text_splitter.split_documents(docs)
        print(f"분할 완료: {len(splits)}개 청크")
        return splits

    @staticmethod
    def prepare_data_for_chroma(splits):
        """Chroma DB에 저장할 텍스트, 메타데이터, ID 준비."""
        texts, metadatas, ids = [], [], []
        for doc in splits:
            texts.append(f"content: {doc.page_content}")
            metadatas.append({
                "emotion": doc.metadata.get('emotion', ''),
            })
            ids.append(doc.metadata.get('doc_id'))

        return texts, metadatas, ids

    @staticmethod
    async def create_embeddings_async(texts: List[str], pbar: tqdm, batch_size: int = 20, concurrent_tasks: int = 5) -> List[List[float]]:
        """텍스트 리스트의 임베딩을 비동기로 생성합니다."""
        embedding_function = OpenAIEmbeddings(
            model="text-embedding-3-small",
            chunk_size=1000
        )
        
        all_embeddings = []
        batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        semaphore = asyncio.Semaphore(concurrent_tasks)
        async def process_batch(batch):
            async with semaphore:
                await asyncio.sleep(0.1)
                return await embedding_function.aembed_documents(batch)
        tasks = [process_batch(batch) for batch in batches]
        for coro in asyncio.as_completed(tasks):
            embeddings = await coro
            if embeddings:
                all_embeddings.extend(embeddings)
                pbar.update(batch_size)
        return all_embeddings

    @staticmethod
    def get_optimal_embedding_params(num_texts: int) -> (int, int):
        """
        입력 텍스트의 총 개수(num_texts)와 CPU 코어 수를 기준으로 최적의 batch_size와
        concurrent_tasks 값을 계산합니다.

        Returns:
            tuple: (batch_size, concurrent_tasks)
        """
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        # 텍스트 수에 따라 배치 크기를 조정하는 간단한 heuristic
        if num_texts < 100:
            batch_size = 10
        elif num_texts < 1000:
            batch_size = 20
        else:
            batch_size = 50

        # 동시 실행 태스크는 CPU 코어 수와 상한값 10을 고려
        concurrent_tasks = min(10, cpu_count)
        print(
            f"Optimal Parameters determined: batch_size={batch_size}, "
            f"concurrent_tasks={concurrent_tasks} based on {num_texts} texts and {cpu_count} CPUs"
        )
        return batch_size, concurrent_tasks

    @staticmethod
    def create_embeddings(texts: List[str]) -> List[List[float]]:
        """동기 방식으로 비동기 임베딩 생성을 실행합니다.
        
        입력 텍스트의 수에 따라 최적의 batch_size와 concurrent_tasks를 계산하여 임베딩을 생성합니다.
        """
        batch_size, concurrent_tasks = RAGProcessor.get_optimal_embedding_params(len(texts))
        with tqdm(total=len(texts), desc="임베딩 생성 중") as pbar:
            embeddings = asyncio.run(
                RAGProcessor.create_embeddings_async(texts, pbar, batch_size, concurrent_tasks)
            )
        return embeddings

    @staticmethod
    def process_files(csv_files: List[str], existing_ids: set, vectorstore, db_dir: str):
        """CSV 파일들을 처리하고 진행상황을 시각화합니다."""
        total_new_docs = 0
        processed_count = 0

        print("\n=== CSV 파일 처리 시작 ===")
        for csv_file in tqdm(csv_files, desc="📂 CSV 파일 처리"):
            try:
                # CSV 파일 로드 및 메타데이터 추가
                docs = RAGProcessor.load_csv_with_metadata(csv_file)
                if not docs:
                    continue

                # 새 문서 필터링
                new_docs = RAGProcessor.filter_new_documents(docs, existing_ids, csv_file)
                if not new_docs:
                    continue

                # 문서 분할
                total_new_docs += len(new_docs)
                splits = RAGProcessor.split_documents(new_docs)
                
                # 데이터 준비
                texts, metadatas, ids = RAGProcessor.prepare_data_for_chroma(splits)
                
                print(f"\n📄 [{os.path.basename(csv_file)}] 처리 중...")
                print(f"   - 텍스트 수: {len(texts)}개")
                
                # 임시 저장된 임베딩 확인
                temp_embeddings = RAGProcessor.load_temp_embeddings(csv_file)
                
                if temp_embeddings is not None:
                    print("💾 기존 임시 임베딩 사용")
                    embeddings = temp_embeddings
                else:
                    print("🔄 새로운 임베딩 생성 시작")
                    embeddings = RAGProcessor.create_embeddings(texts)
                    RAGProcessor.save_temp_embeddings(csv_file, embeddings)
                
                # Chroma DB 업데이트
                vectorstore = RAGProcessor.update_chroma_db(
                    vectorstore, texts, embeddings, metadatas, ids, db_dir
                )
                
                # 처리 완료 기록
                RAGProcessor.save_processed_file_info(csv_file)
                processed_count += 1
                print(f"✅ [{os.path.basename(csv_file)}] 처리 완료\n")

            except Exception as e:
                print(f"❌ 파일 처리 중 오류 발생 ({os.path.basename(csv_file)}): {e}")
                continue

        return vectorstore, total_new_docs, processed_count

    @staticmethod
    def update_chroma_db(vectorstore, texts, embeddings, metadatas, ids, db_dir):
        """Chroma DB에 데이터를 배치 단위로 추가하고 진행상황을 표시합니다."""
        MAX_BATCH_SIZE = 5000

        if vectorstore is None:
            print("🔨 새로운 Chroma DB 생성 중...")
            embedding_function = OpenAIEmbeddings(model="text-embedding-3-small")
            vectorstore = Chroma(
                persist_directory=db_dir,
                embedding_function=embedding_function,
                collection_name="korean_dialogue"
            )

        total_batches = (len(texts) + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
        print(f"📦 Chroma DB 업데이트 시작 (총 {total_batches}개 배치)")
        
        for i in tqdm(range(0, len(texts), MAX_BATCH_SIZE), desc="💫 DB 업데이트"):
            end_idx = min(i + MAX_BATCH_SIZE, len(texts))
            vectorstore._collection.add(
                embeddings=embeddings[i:end_idx],
                documents=texts[i:end_idx],
                metadatas=metadatas[i:end_idx],
                ids=ids[i:end_idx]
            )
        
        print(f"✨ DB 업데이트 완료 (총 {len(texts)}개 문서)")
        return vectorstore

    @staticmethod
    async def async_update_chroma_db(vectorstore, texts, embeddings, metadatas, ids, db_dir):
        """
        비동기 방식으로 Chroma DB를 업데이트합니다.
        최대 배치 사이즈 5000개를 고려하여 vectorstore._collection.add 호출을
        asyncio.to_thread로 감싸서 동시에 실행합니다.

        Returns:
            업데이트된 vectorstore 인스턴스.
        """
        MAX_BATCH_SIZE = 5000
        total_batches = (len(texts) + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
        print(f"📦 비동기 Chroma DB 업데이트 시작 (총 {total_batches}개 배치)")
        tasks = []
        for i in range(0, len(texts), MAX_BATCH_SIZE):
            end_idx = min(i + MAX_BATCH_SIZE, len(texts))
            tasks.append(
                asyncio.to_thread(
                    vectorstore._collection.add,
                    embeddings=embeddings[i:end_idx],
                    documents=texts[i:end_idx],
                    metadatas=metadatas[i:end_idx],
                    ids=ids[i:end_idx]
                )
            )
        await asyncio.gather(*tasks)
        print(f"✨ 비동기 DB 업데이트 완료 (총 {len(texts)}개 문서)")
        return vectorstore

    @staticmethod
    def save_processed_file_info(csv_file):
        """처리된 파일 정보를 DB에 저장."""
        RAG_DB.objects.create(file_name=os.path.basename(csv_file), file_path=csv_file)

    @staticmethod
    def get_temp_embedding_path(file_name):
        """임시 임베딩 파일 경로를 반환합니다."""
        if not os.path.exists(RAGProcessor.TEMP_DIR):
            os.makedirs(RAGProcessor.TEMP_DIR)
        return os.path.join(RAGProcessor.TEMP_DIR, f"{os.path.basename(file_name)}.pkl")

    @staticmethod
    def save_temp_embeddings(file_name, data):
        """임베딩 데이터를 임시 파일로 저장합니다."""
        temp_path = RAGProcessor.get_temp_embedding_path(file_name)
        with open(temp_path, 'wb') as f:
            pickle.dump(data, f)

    @staticmethod
    def load_temp_embeddings(file_name):
        """임시 저장된 임베딩 데이터를 로드합니다."""
        temp_path = RAGProcessor.get_temp_embedding_path(file_name)
        if os.path.exists(temp_path):
            with open(temp_path, 'rb') as f:
                return pickle.load(f)
        return None

    @staticmethod
    def process_conversation_json(conversation, existing_ids, vectorstore):
        """
        conversation: 대화 JSON으로, "info"와 "utterances" 키를 포함해야 합니다.
        existing_ids: 이미 처리된 문서의 ID 집합
        vectorstore: 벡터 데이터베이스 인스턴스
        
        이 함수는 conversation에서 각 utterance의 텍스트를 추출하고, 
        기존에 처리된 문서는 건너뛴 후 새로운 텍스트들을 vectorstore에 추가합니다.
        
        Returns:
            vectorstore, new_docs (int), processed_count (int)
        """
        new_docs = 0
        processed_count = 0
        texts = []
        metadatas = []
        # 예시: 각 utterance는 "text" 필드를 포함한 dict라고 가정
        for utter in conversation.get("utterances", []):
            text = utter.get("text", "").strip()
            if not text:
                continue
            doc_id = hash(text)  # 단순 해시 사용; 실제 환경에서는 더 안전한 방법 사용 권장
            if doc_id in existing_ids:
                continue
            texts.append(text)
            metadata = {
                "source": conversation.get("info", {}).get("source", "json"),
                "doc_id": doc_id
            }
            metadatas.append(metadata)
            new_docs += 1
            processed_count += 1
        
        if texts:
            # vectorstore에 텍스트와 메타데이터 추가 (메서드 명칭은 실제 구현에 맞게 수정)
            vectorstore.add_texts(texts, metadatas)
        
        return vectorstore, new_docs, processed_count

class RAGQuery:
    @staticmethod
    def create_qa_chain():
        """공유된 DB_DIR을 사용하여 QA 체인 생성"""
        db_dir = RAGProcessor.DB_DIR
        vectorstore = Chroma(
            persist_directory=db_dir,
            embedding_function=OpenAIEmbeddings(
                model="text-embedding-3-small"
            ),
            collection_name="korean_dialogue"
        )
        
        # 필터 제거하고 테스트
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 10},  # 상위 10개 결과
            filter={"emotion": "happy"},
        )
        
        # 디버깅을 위한 컬렉션 정보 출력
        print(f"컬렉션 내 문서 수: {vectorstore._collection.count()}")
        
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=1.1
        )

        # 프롬프트 템플릿 수정: 채팅 히스토리와 리트리브된 문서를 별도의 키로 전달
        template = """Given the chat history and the retrieved context, rephrase the partner's harsh message into a gentle, warm, and loving tone that fits naturally into your ongoing conversation.
        
        Chat History:
        {chat_history}
        
        Retrieved Context:
        {retrieved_context}
        
        Partner's harsh message:
        {question}
        
        Instructions:
          1. Carefully analyze the chat history to grasp the emotional cues.
          2. Incorporate relevant context from the retrieved documents.
          3. Rephrase the partner's message, keeping its original meaning while softening the tone into a caring and respectful manner.
          4. Provide three alternative rephrasings separated by pipes (|).
          5. Each alternative should be concise (aim for around 15 words) and crafted for a loving conversation.
          6. (Important) Whatever the language of the Chat History and Retrieved Context is, always respond in the same language as the harsh message "{question}"!!
        
        Response Format:
        Alternative1 | Alternative2 | Alternative3
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm
        
        return retriever, chain

    @staticmethod
    def get_answer(question: str):
        # chat_message 테이블(모델)에서 대화 히스토리 가져오기
        from chat.models import Message

        # 시간순으로 정렬된 전체 채팅 메시지로 대화 맥락 구성
        messages = Message.objects.all().order_by('created_at')
        chat_history = "\n".join([f"{msg.user}: {msg.input_content}" for msg in messages])

        # 벡터스토어에서 추가적인 문서(대화 관련 문맥) 가져오기
        retriever, chain = RAGQuery.create_qa_chain()
        retrieved_docs = retriever.invoke(question)
        retrieved_context = "\n".join([doc.page_content for doc in retrieved_docs])

        print(f"Chat History: {chat_history}")
        print(f"Retrieved Context: {retrieved_context}")
        result = chain.invoke({
            "chat_history": chat_history,
            "retrieved_context": retrieved_context,
            "question": question
        })
        return result.content
    
    @staticmethod
    def create_qa_chain_with_emotion():
        """공유된 DB_DIR을 사용하여 QA 체인 생성"""
        db_dir = RAGProcessor.DB_DIR
        vectorstore = Chroma(
            persist_directory=db_dir,
            embedding_function=OpenAIEmbeddings(
                model="text-embedding-3-small"
            ),
            collection_name="korean_dialogue"
        )
        
        # 필터 제거하고 테스트
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 10},
        )
        
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7
        )

        # 프롬프트 템플릿 수정: 채팅 히스토리와 리트리브된 문서를 별도의 키로 전달
        template = """리트리브된 문장 예시를 참고하여 입력된 메시지에 대한 감정을 분석하고, 해당메세지의 감정을 생성하세요.
        
        리트리브된 문서:
        {retrieved_context}
        
        입력된 메시지:
        {question}
        
        감정:
        """
        
        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm
        
        return retriever, chain

    @staticmethod
    def get_answer(question: str):
        # chat_message 테이블(모델)에서 대화 히스토리 가져오기
        from chat.models import Message

        # 시간순으로 정렬된 전체 채팅 메시지로 대화 맥락 구성
        messages = Message.objects.all().order_by('created_at')
        chat_history = "\n".join([f"{msg.user}: {msg.input_content}" for msg in messages])

        # 벡터스토어에서 추가적인 문서(대화 관련 문맥) 가져오기
        retriever, chain = RAGQuery.create_qa_chain()
        retrieved_docs = retriever.invoke(question)
        retrieved_context = "\n".join([doc.page_content for doc in retrieved_docs])

        print(f"Chat History: {chat_history}")
        print(f"Retrieved Context: {retrieved_context}")
        result = chain.invoke({
            "chat_history": chat_history,
            "retrieved_context": retrieved_context,
            "question": question
        })
        return result.content
        
        
    @staticmethod
    def get_answer_with_emotion(question: str):
        # chat_message 테이블(모델)에서 대화 히스토리 가져오기
        from chat.models import Message

        retriever, chain = RAGQuery.create_qa_chain_with_emotion()
        retrieved_docs = retriever.invoke(question)
        retrieved_context = "\n".join([doc.page_content for doc in retrieved_docs])

        result = chain.invoke({
            "question": question,
            "retrieved_context": retrieved_context
        })
        return result.content

