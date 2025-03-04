from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from rest_framework.permissions import AllowAny

from .method import SimpleRAG
from .models import EmbeddingFile
from .serializers import EmbeddingFileSerializer
from .services.embedding_service import EmbeddingService

import os
import logging

# 기본 설정
logger = logging.getLogger(__name__)

# SimpleRAG에서 정의된 경로 사용
DB_DIR = SimpleRAG.DB_DIR

# DB_DIR이 존재하지 않으면 생성
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class EmbeddingFileViewSet(viewsets.ModelViewSet):
    """
    임베딩 파일 목록 관리 API
    """
    queryset = EmbeddingFile.objects.all().order_by('-created_at')
    serializer_class = EmbeddingFileSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['file_name', 'file_path', 'created_at']
    search_fields = ['file_name', 'file_path']
    ordering_fields = ['file_name', 'created_at']
    permission_classes = [AllowAny]  # 테스트를 위해 권한 요구 제거

class RAGAutoEmbedView(APIView):
    """
    지정된 디렉토리의 파일을 자동으로 임베딩합니다.
    """
    permission_classes = [AllowAny]  # 테스트를 위해 권한 요구 제거
    
    def post(self, request, *args, **kwargs):
        try:
            # 1. 요청에서 매개변수 가져오기
            data_dir = request.data.get('data_dir', 'data')
            file_types = request.data.get('file_types', ['csv'])
            force_reprocess = request.data.get('force_reprocess', False)
            
            # 2. 임베딩 서비스를 사용하여 파일 처리
            results = EmbeddingService.process_all_files(
                data_dir=data_dir,
                file_types=file_types,
                force_reprocess=force_reprocess
            )
            
            # 3. 응답 반환
            return Response({
                'status': 'success',
                'message': f"{results['new_files_processed']}개 파일 처리 완료",
                'details': results
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"자동 임베딩 처리 중 오류 발생: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RAGManualEmbedView(APIView):
    """
    지정된 파일을 수동으로 임베딩합니다.
    """
    permission_classes = [AllowAny]  # 테스트를 위해 권한 요구 제거
    
    def post(self, request, *args, **kwargs):
        try:
            # 1. 요청에서 파일 경로 가져오기
            file_path = request.data.get('file_path')
            file_type = request.data.get('file_type', 'csv')
            
            if not file_path:
                return Response({
                    'status': 'error',
                    'message': '파일 경로가 필요합니다'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. 파일 임베딩 처리
            result = EmbeddingService.process_file(file_path, file_type)
            
            # 3. 응답 반환
            if result['status'] == 'success':
                return Response({
                    'status': 'success',
                    'message': '파일 임베딩 완료',
                    'details': result
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'message': result.get('message', '파일 처리 실패'),
                    'details': result
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"수동 임베딩 처리 중 오류 발생: {str(e)}", exc_info=True)
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

