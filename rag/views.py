from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.parsers import JSONParser
from .method import RAGProcessor, RAGQuery
from .models import RAG_DB, RAG
from .serializers import RAGSerializer
from accounts.models import User
from dotenv import load_dotenv
import os
from tqdm import tqdm
import json
import time
import glob
import rdflib
from rdflib import URIRef

# 환경 변수 로드
load_dotenv()

# RAGProcessor에서 정의된 경로 사용
DB_DIR = RAGProcessor.DB_DIR
CSV_PATTERN = "data/rag/*.csv"

# DB_DIR이 존재하지 않으면 생성
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)

class RAGViewSet(viewsets.ReadOnlyModelViewSet):
    """
    사용자의 RAG 쿼리 기록을 조회하는 뷰셋
    """
    queryset = RAG.objects.all().order_by('-created_at')
    serializer_class = RAGSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user__user_id=user_id)
        return queryset

class RAGQueryView(APIView):
    """
    RAG 시스템에 질의하는 API 뷰
    
    Endpoints:
        GET /rag/query/: API 사용 방법 반환
        POST /rag/query/: RAG 시스템에 질의
    """
    parser_classes = (JSONParser,)
    permission_classes = []  # 인증 비활성화
    
    def get(self, request):
        """API 사용 방법을 반환합니다."""
        return Response({
            'message': 'RAG 쿼리 API',
            'usage': {
                'method': 'POST',
                'description': 'RAG 시스템에 질의합니다.',
                'endpoint': '/v1/rag/query/',
                'parameters': {
                    'query': '(필수) 쿼리 텍스트',
                    'max_tokens': '(선택) 응답 최대 토큰 수',
                    'use_maternal_health': '(선택) 산모 건강 데이터 사용 여부 (기본값: true)',
                    'user_id': '(선택) 사용자 ID'
                }
            }
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """RAG 시스템에 질의합니다. 모든 질문은 산모가 하는 것으로 간주합니다."""
        try:
            query = request.data.get('query')
            max_tokens = request.data.get('max_tokens', 150)
            use_maternal_health = request.data.get('use_maternal_health', True)  # 기본값을 True로 변경
            user_id = request.data.get('user_id')
            
            if not query:
                return Response({
                    'error': '쿼리가 제공되지 않았습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 모든 질문을 산모 건강 관련 질문으로 처리
            retriever, chain = RAGQuery.create_maternal_health_qa_chain()
            retrieved_docs = retriever.invoke(query)
            retrieved_context = "\n".join([doc.page_content for doc in retrieved_docs])
            answer = chain.invoke({
                "retrieved_context": retrieved_context,
                "question": query
            }).content
            
            # 결과 저장
            rag_entry = RAG(
                question=query,
                answer=answer
            )
            
            # 사용자 ID가 제공된 경우 사용자 연결
            if user_id:
                try:
                    user = User.objects.get(user_id=user_id)
                    rag_entry.user = user
                except User.DoesNotExist:
                    pass  # 사용자가 존재하지 않는 경우 무시
            
            rag_entry.save()
            
            return Response({
                'query': query,
                'answer': answer,
                'sources': [doc.metadata for doc in retrieved_docs],
                'processing_time': f"{time.time() - time.time():.2f}초"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Error code: {e.__class__.__name__} - {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RAGAutoEmbedView(APIView):
    """
    data 폴더의 모든 파일을 자동으로 임베딩하는 API 뷰
    
    Endpoints:
        GET /rag/auto-embed/: API 사용 방법 반환
        POST /rag/auto-embed/: 모든 데이터 파일 자동 임베딩
    """
    permission_classes = []  # 인증 비활성화
    
    def get(self, request):
        """API 사용 방법을 반환합니다."""
        return Response({
            'message': '자동 임베딩 API',
            'usage': {
                'method': 'POST',
                'description': 'data 폴더의 모든 파일을 자동으로 임베딩합니다.',
                'endpoint': '/v1/rag/auto-embed/',
                'parameters': {
                    'data_dir': '(선택) 데이터 디렉토리 경로. 기본값은 "data"',
                    'file_types': '(선택) 처리할 파일 유형 목록. 기본값은 ["csv", "json", "rdf", "xml"]',
                    'force_reprocess': '(선택) 이미 처리된 파일도 다시 처리할지 여부. 기본값은 false'
                }
            }
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """모든 데이터 파일을 자동으로 임베딩합니다."""
        try:
            data_dir = request.data.get('data_dir', 'data')
            file_types = request.data.get('file_types', ['csv', 'json', 'rdf', 'xml'])
            force_reprocess = request.data.get('force_reprocess', False)
            
            # 결과 저장 변수
            results = {
                'total_files_found': 0,
                'new_files_processed': 0,
                'skipped_files': 0,
                'failed_files': 0,
                'total_documents_embedded': 0,
                'processing_time': 0,
                'file_details': []
            }
            
            # 처리할 파일 목록 생성
            all_files = []
            for file_type in file_types:
                file_pattern = os.path.join(data_dir, f"**/*.{file_type}")
                files = glob.glob(file_pattern, recursive=True)
                for file in files:
                    all_files.append((file, file_type))
            
            results['total_files_found'] = len(all_files)
            
            # 이미 처리된 파일 목록 가져오기
            processed_files = set(RAG_DB.objects.values_list('file_path', flat=True))
            
            # 시작 시간 기록
            start_time = time.time()
            
            # 파일 처리
            with tqdm(total=len(all_files), desc="📂 전체 파일 진행률") as pbar:
                # 초기 진행률 메시지 설정
                pbar.set_postfix_str(f"처리: 0개, 스킵: 0개")
                
                for file_path, file_type in all_files:
                    file_result = {
                        'file_path': file_path,
                        'file_type': file_type,
                        'status': '',
                        'documents_embedded': 0
                    }
                    
                    try:
                        # 이미 처리된 파일인지 확인
                        if file_path in processed_files and not force_reprocess:
                            file_result['status'] = 'skipped (already processed)'
                            results['skipped_files'] += 1
                            results['file_details'].append(file_result)
                            pbar.update(1)
                            # 스킵된 파일 표시
                            pbar.set_postfix_str(f"처리: {results['new_files_processed']}개, 스킵: {results['skipped_files']}개")
                            continue
                        
                        # force_reprocess=true이고 이미 처리된 파일인 경우, 기존 레코드 삭제
                        if file_path in processed_files and force_reprocess:
                            RAG_DB.objects.filter(file_path=file_path).delete()
                        
                        # 파일 확장자 확인
                        file_ext = os.path.splitext(file_path)[1].lower()
                        
                        # 파일 이름에서 건강 관련 키워드 확인
                        file_name = os.path.basename(file_path).lower()
                        health_keywords = ['health', 'medical', 'wellness', '건강', '의료', '웰니스', '산모', '임신', '출산', 'maternal', 'pregnancy']
                        is_health_related = any(keyword in file_name for keyword in health_keywords)
                        
                        if file_ext == '.csv':
                            # CSV 파일 처리
                            vectorstore, existing_ids = RAGProcessor.initialize_chroma_db()
                            
                            # CSV 파일 로드 및 메타데이터 추가
                            docs = RAGProcessor.load_csv_with_metadata(file_path)
                            if not docs:
                                raise ValueError("CSV 파일을 로드할 수 없습니다.")
                            
                            # 새 문서 필터링
                            new_docs = RAGProcessor.filter_new_documents(docs, existing_ids, file_path)
                            
                            # 문서 분할
                            splits = RAGProcessor.split_documents(new_docs)
                            
                            # 데이터 준비
                            texts, metadatas, ids = RAGProcessor.prepare_data_for_chroma(splits)
                            
                            # 임베딩 생성
                            embeddings = RAGProcessor.create_embeddings(texts)
                            
                            # Chroma DB 업데이트
                            RAGProcessor.update_chroma_db(
                                vectorstore, texts, embeddings, metadatas, ids, DB_DIR
                            )
                            
                            # 처리 완료 기록
                            RAG_DB.objects.create(file_name=os.path.basename(file_path), file_path=file_path)
                            
                            file_result['status'] = 'success'
                            file_result['documents_embedded'] = len(new_docs)
                            results['total_documents_embedded'] += len(new_docs)
                            
                        elif file_ext == '.json':
                            # JSON 파일 처리
                            with open(file_path, "r", encoding="utf-8") as f:
                                file_content = f.read()
                            
                            try:
                                conversation = json.loads(file_content)
                            except Exception as e:
                                raise ValueError(f"유효하지 않은 JSON 파일: {str(e)}")
                            
                            # 필수 키 체크: info와 utterances 필요
                            if not {"info", "utterances"}.issubset(conversation.keys()):
                                raise ValueError("JSON 파일은 info와 utterances 키를 포함해야 합니다.")
                            
                            # Chroma DB 초기화
                            vectorstore, existing_ids = RAGProcessor.initialize_chroma_db()
                            
                            # JSON 파일 처리
                            vectorstore, new_docs, count = RAGProcessor.process_conversation_json(
                                conversation, existing_ids, vectorstore
                            )
                            
                            # 처리 완료 기록
                            RAG_DB.objects.create(file_name=os.path.basename(file_path), file_path=file_path)
                            
                            file_result['status'] = 'success'
                            file_result['documents_embedded'] = new_docs
                            results['total_documents_embedded'] += new_docs
                            
                        elif file_ext in ['.rdf', '.xml', '.n-triples', '.nt']:
                            # RDF 파일 처리
                            # 건강 관련 파일인 경우 산모 건강 데이터 처리 방식 사용
                            if is_health_related:
                                print(f"건강 관련 데이터로 처리: {file_path}")
                                # n-triples 파일인 경우 직접 파싱 방식 사용
                                if file_ext in ['.n-triples', '.nt']:
                                    result = RAGProcessor.embed_maternal_health_data_from_ntriples(file_path, format='nt')
                                else:
                                    result = RAGProcessor.embed_maternal_health_data(file_path)
                            else:
                                # 일반 RDF 파일 처리
                                result = RAGProcessor.process_rdf_data(file_path)
                            
                            # 처리 완료 기록
                            RAG_DB.objects.create(file_name=os.path.basename(file_path), file_path=file_path)
                            
                            file_result['status'] = 'success'
                            file_result['documents_embedded'] = result.get('embedded_resources', 0)
                            results['total_documents_embedded'] += result.get('embedded_resources', 0)
                        
                        results['new_files_processed'] += 1
                        # 처리된 파일 수 표시
                        pbar.set_postfix_str(f"처리: {results['new_files_processed']}개, 스킵: {results['skipped_files']}개")
                        
                    except Exception as e:
                        file_result['status'] = 'failed'
                        file_result['error'] = str(e)
                        results['failed_files'] += 1
                        # 실패한 파일 표시
                        pbar.set_postfix_str(f"처리: {results['new_files_processed']}개, 스킵: {results['skipped_files']}개, 실패: {results['failed_files']}개")
                    
                    results['file_details'].append(file_result)
                    pbar.update(1)
            
            # 처리 시간 계산
            end_time = time.time()
            results['processing_time'] = round(end_time - start_time, 2)
            
            # 결과 요약 생성
            summary = {
                'message': '자동 임베딩 완료',
                'total_files_found': results['total_files_found'],
                'new_files_processed': results['new_files_processed'],
                'skipped_files': results['skipped_files'],
                'failed_files': results['failed_files'],
                'total_documents_embedded': results['total_documents_embedded'],
                'processing_time_seconds': results['processing_time'],
                'file_details': results['file_details']
            }
            
            return Response(summary, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

