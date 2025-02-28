from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser
from .method import RAGProcessor, RAGQuery
from dotenv import load_dotenv
import os
from tqdm import tqdm
import json

# 환경 변수 로드
load_dotenv()

# RAGProcessor에서 정의된 경로 사용
DB_DIR = RAGProcessor.DB_DIR
CSV_PATTERN = "data/rag/*.csv"

# DB_DIR이 존재하지 않으면 생성
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)

class RAGSetupView(APIView):
    """
    RAG 시스템 초기 설정을 위한 API 뷰
    
    Endpoints:
        POST /rag/setup/: CSV 파일을 읽어 Chroma DB에 임베딩을 저장
    """

    def get(self, request):
        """API 엔드포인트 설명을 반환합니다."""
        return Response({
            'message': 'RAG 시스템 설정 API',
            'usage': {
                'method': 'POST',
                'description': 'CSV 파일을 처리하여 RAG 시스템의 벡터 데이터베이스를 구축합니다.',
                'endpoint': '/v1/rag/setup/'
            }
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """
        CSV 파일을 처리하여 RAG 시스템의 벡터 데이터베이스를 구축합니다.
        
        Process:
            1. CSV 파일 로드 및 전처리
            2. 새로운(미처리) 파일 필터링
            3. Chroma DB 초기화
            4. 각 CSV 파일별 처리:
                - 메타데이터와 함께 문서 로드
                - 새로운 문서 필터링
                - 문서 분할(청크)
                - Chroma DB에 데이터 저장
            5. 처리 결과 반환
        
        Returns:
            Response: {
                'message': str,
                'processed_files': int,
                'new_docs': int,
                'total_docs': int
            }
        """

        try:
            # 1. CSV 파일 로드
            csv_files = RAGProcessor.load_and_preprocess_csv(CSV_PATTERN)
            new_files = RAGProcessor.filter_processed_files(csv_files)

            # 2. 새로운 파일이 없는 경우 처리
            if not new_files:
                return Response({
                    'message': '새로운 파일이 없습니다.',
                    'processed_files': len(csv_files)
                }, status=status.HTTP_200_OK)

            # 3. Chroma DB 초기화
            vectorstore, existing_ids = RAGProcessor.initialize_chroma_db()

            # 4. 파일 처리 및 DB 업데이트
            vectorstore, total_new_docs, processed_count = RAGProcessor.process_files(
                new_files, existing_ids, vectorstore, RAGProcessor.DB_DIR
            )

            # 5. 처리 결과 반환
            if vectorstore:
                total_docs = vectorstore._collection.count()
                return Response({
                    'message': '새로운 데이터 처리 완료',
                    'processed_files': processed_count,
                    'new_docs': total_new_docs,
                    'total_docs': total_docs
                }, status=status.HTTP_201_CREATED)

            return Response({
                'message': '처리된 문서가 없습니다.',
                'processed_files': processed_count
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RAGQueryView(APIView):
    parser_classes = (JSONParser,)
    """
    RAG 질의응답 API
    
    Endpoints:
        POST /rag/query/: 사용자 질문에 대한 답변을 생성
    """
    def get(self, request):
        """API 사용 방법을 반환합니다."""
        return Response({
            "question": "너 지금 또 감정적이야"
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """사용자 질문에 대한 답변을 생성합니다."""
        try:
            # 질문 추출
            question = request.data.get('question')
            if not question:
                return Response(
                    {'error': '질문이 필요합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 답변 생성
            result = RAGQuery.get_answer(question)
            
            # 출력값 정리 - 따옴표와 백슬래시 제거
            cleaned_output = result.replace('"', '').replace('\\', '')
            
            return Response(cleaned_output, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RAGJsonSetupView(APIView):
    parser_classes = (JSONParser,)

    def post(self, request):
        """
        JSON 파일을 처리하여 RAG 시스템의 벡터 데이터베이스를 구축합니다.
        
        JSON 파일은 다음 두 가지 형식 중 하나로 전달될 수 있습니다.
          - JSON 문자열: 'json_file' 키에 문자열 형식으로 전달되며 내부에서 파싱함.
          - 이미 파싱된 JSON 객체: 'json_file' 키에 딕셔너리 형식으로 전달됨.
          
        필수적으로, JSON 데이터는 "info"와 "utterances" 키를 포함해야 합니다.
        """
        try:
            json_file = request.data.get('json_file')
            if not json_file:
                return Response(
                    {'error': 'JSON 파일이 필요합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 문자열 형태면 JSON 파싱 시도
            if isinstance(json_file, str):
                try:
                    conversation = json.loads(json_file)
                except Exception:
                    return Response(
                        {'error': '유효한 JSON 파일 형식이 아닙니다.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            # 이미 파싱된 JSON 객체인 경우
            elif isinstance(json_file, dict):
                conversation = json_file
            else:
                return Response(
                    {'error': '잘못된 JSON 데이터 형식입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 필수 키 체크: info와 utterances 필요
            if not {"info", "utterances"}.issubset(conversation.keys()):
                return Response(
                    {'error': 'JSON 파일은 info와 utterances 키를 포함해야 합니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 1. Chroma DB 초기화
            vectorstore, existing_ids = RAGProcessor.initialize_chroma_db()
            
            # 2. JSON 파일을 통한 대화 데이터 처리 및 임베딩 생성
            vectorstore, total_new_docs, processed_count = RAGProcessor.process_conversation_json(
                conversation, existing_ids, vectorstore
            )
            
            # 3. 최종 DB 내 총 문서 수 확인
            total_docs = vectorstore._collection.count()
            return Response({
                'message': 'JSON 파일 처리 완료',
                'processed_items': processed_count,
                'new_docs': total_new_docs,
                'total_docs': total_docs
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RAGBulkJsonSetupView(APIView):
    """
    데이터 디렉터리(data/rag/) 아래에 있는 모든 JSON 파일을 처리하여
    RAG 시스템의 벡터 데이터베이스를 구축하는 API 뷰.
    
    Endpoints:
        GET  /rag/bulk-json-setup/ : API 사용 방법 반환
        POST /rag/bulk-json-setup/ : data/rag/ 폴더의 모든 JSON 파일 처리
    """
    def get(self, request):
        """API 사용 방법을 반환합니다."""
        return Response({
            'message': '데이터 디렉터리 내의 모든 JSON 파일을 처리합니다. POST 요청을 사용하여 실행합니다.',
            'usage': {
                'method': 'POST',
                'description': '서버의 data/rag/ 폴더에 있는 JSON 파일들을 처리하여 벡터 데이터베이스를 구성합니다.',
                'endpoint': '/v1/rag/bulk-json-setup/'
            }
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """
        데이터 디렉터리(data/rag/) 아래 모든 JSON 파일을 처리합니다.
        
        프로세스:
            1. data/rag/ 폴더에서 *.json 파일 검색
            2. 각 JSON 파일에 대해:
               - 파일 읽기 및 JSON 파싱
               - 필수 키("info", "utterances") 확인
               - RAGProcessor.process_conversation_json() 함수를 호출하여 벡터 생성 및 DB 업데이트
            3. 처리 결과(처리된 파일 수, 새 문서 수, 총 문서 수) 반환
        """
        try:
            import glob
            import json

            JSON_PATTERN = "data/rag/TL_기쁨_연인/*.json"
            json_files = glob.glob(JSON_PATTERN)
            if not json_files:
                return Response({
                    'message': '처리할 JSON 파일이 없습니다.'
                }, status=status.HTTP_200_OK)
            
            # Chroma DB 초기화
            vectorstore, existing_ids = RAGProcessor.initialize_chroma_db()
            total_new_docs = 0
            processed_count = 0

            for file_path in tqdm(json_files, desc="JSON 파일 처리"):
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                try:
                    conversation = json.loads(file_content)
                except Exception:
                    # 유효하지 않은 JSON 파일은 건너뜁니다.
                    continue

                # 필수 키 체크: info와 utterances 필요
                if not {"info", "utterances"}.issubset(conversation.keys()):
                    continue

                # JSON 파일 처리
                vectorstore, new_docs, count = RAGProcessor.process_conversation_json(
                    conversation, existing_ids, vectorstore
                )
                total_new_docs += new_docs
                processed_count += count
            
            total_docs = vectorstore._collection.count() if vectorstore else 0
            return Response({
                'message': '모든 JSON 파일 처리 완료',
                'processed_files': processed_count,
                'new_docs': total_new_docs,
                'total_docs': total_docs
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RAGEmotionQueryView(APIView):
    parser_classes = (JSONParser,)
    
    def post(self, request):
        """사용자 질문에 대한 감정을 생성합니다."""
        try:
            question = request.data.get('question')
            if not question:
                return Response(
                    {'error': '질문이 필요합니다.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = RAGQuery.get_answer_with_emotion(question)
            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
