from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from .models import EmbeddingFile
from .services.embedding_service import EmbeddingService
from .method import SimpleRAG


class EmbeddingServiceTestCase(TestCase):
    """
    EmbeddingService 클래스 테스트
    """
    
    def setUp(self):
        """테스트 환경 설정"""
        # 테스트용 임시 디렉토리 생성
        self.test_dir = tempfile.mkdtemp()
        
        # 테스트용 CSV 파일 생성
        self.csv_content = b"id,name,description\n1,test,This is a test"
        self.csv_file_path = os.path.join(self.test_dir, "test.csv")
        with open(self.csv_file_path, "wb") as f:
            f.write(self.csv_content)
            
    def tearDown(self):
        """테스트 완료 후 정리"""
        # 테스트용 임시 디렉토리 삭제
        shutil.rmtree(self.test_dir)
        
        # 테스트 중 생성된 EmbeddingFile 객체 삭제
        EmbeddingFile.objects.all().delete()
    
    def test_get_all_files(self):
        """get_all_files 메서드 테스트"""
        # 테스트 실행
        file_types = ['csv']
        files = EmbeddingService.get_all_files(self.test_dir, file_types)
        
        # 결과 검증
        self.assertEqual(len(files), 1)
        file_paths = [f[0] for f in files]
        self.assertIn(self.csv_file_path, file_paths)
    
    def test_get_processed_files(self):
        """get_processed_files 메서드 테스트"""
        # 테스트 데이터 설정
        EmbeddingFile.objects.create(
            id="00000000-0000-0000-0000-000000000001",
            file_name="test1.csv", 
            file_path="/path/to/test1.csv"
        )
        EmbeddingFile.objects.create(
            id="00000000-0000-0000-0000-000000000002",
            file_name="test2.csv", 
            file_path="/path/to/test2.csv"
        )
        
        # 테스트 실행
        processed_files = EmbeddingService.get_processed_files()
        
        # 결과 검증
        self.assertEqual(len(processed_files), 2)
        self.assertIn("/path/to/test1.csv", processed_files)
        self.assertIn("/path/to/test2.csv", processed_files)
    
    @patch('rag.method.SimpleRAG.process_file')
    @patch('os.path.splitext')
    @patch('os.path.basename')
    def test_process_file(self, mock_basename, mock_splitext, mock_process_file):
        """process_file 메서드 테스트"""
        # SimpleRAG.process_file 모킹
        mock_process_file.return_value = True
        
        # os.path 함수 모킹
        mock_splitext.return_value = ("test", ".csv")
        mock_basename.return_value = "test.csv"
        
        # 테스트 실행
        with patch.object(EmbeddingFile.objects, 'create') as mock_create:
            result = EmbeddingService.process_file(self.csv_file_path, "csv")
        
        # 결과 검증
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['file_path'], self.csv_file_path)
        self.assertEqual(result['file_type'], "csv")
        mock_create.assert_called_once()


# 클래스 수준 패치 사용
@patch('rag.views.EmbeddingService')
class RAGAPITestCase(TestCase):
    """
    RAG API 엔드포인트 테스트
    """
    
    def setUp(self):
        """테스트 환경 설정"""
        self.client = Client()
        
    def test_auto_embed_post(self, mock_embedding_service):
        """자동 임베딩 API POST 요청 테스트"""
        # 모의 반환값 설정
        mock_embedding_service.process_all_files.return_value = {
            'total_files_found': 5,
            'new_files_processed': 3,
            'skipped_files': 2,
            'failed_files': 0,
            'processing_time': 2.5,
            'file_details': []
        }
        
        # 테스트 데이터
        data = {
            'data_dir': 'test_data',
            'file_types': ['csv'],
            'force_reprocess': True
        }
        
        # URL 이름 업데이트 - test_auto-embed는 Django 테스트에서 문제가 될 수 있으므로 직접 경로 지정
        url = '/v1/rag/auto-embed/'
        
        # API 호출에 성공해야 함
        response = self.client.post(
            url,
            data=data,
            content_type='application/json'
        )
        
        # 응답 검증
        self.assertEqual(response.status_code, 200)
        
        # 함수 호출 검증
        mock_embedding_service.process_all_files.assert_called_once()
    
    def test_manual_embed_post(self, mock_embedding_service):
        """수동 임베딩 API POST 요청 테스트"""
        # 모의 반환값 설정
        mock_embedding_service.process_file.return_value = {
            'status': 'success',
            'file_path': '/path/to/test.csv',
            'file_type': 'csv',
            'documents_embedded': 1
        }
        
        # 테스트 데이터
        data = {
            'file_path': '/path/to/test.csv',
            'file_type': 'csv'
        }
        
        # URL 직접 지정
        url = '/v1/rag/manual-embed/'
        
        # API 호출
        response = self.client.post(
            url,
            data=data,
            content_type='application/json'
        )
        
        # 응답 검증
        self.assertEqual(response.status_code, 200)
        
        # 함수 호출 검증
        mock_embedding_service.process_file.assert_called_once()
