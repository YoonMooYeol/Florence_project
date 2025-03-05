import os
import time
import glob
from typing import Dict, List, Tuple, Set, Any
from django.conf import settings

from ..models import EmbeddingFile
from ..method import SimpleRAG

class EmbeddingService:
    """
    파일 임베딩 처리를 위한 서비스 클래스
    
    CSV 파일을 찾아서 SimpleRAG를 사용해 
    벡터 데이터베이스에 임베딩하는 기능을 제공합니다.
    """
    
    @staticmethod
    def get_all_files(data_dir: str, file_types: List[str]) -> List[Tuple[str, str]]:
        """
        지정된 디렉토리에서 특정 타입의 모든 파일을 찾습니다.
        
        Args:
            data_dir: 파일을 찾을 디렉토리 경로
            file_types: 찾을 파일 확장자 목록
            
        Returns:
            (파일 경로, 파일 타입) 튜플 목록
        """
        all_files = []
        for file_type in file_types:
            # 지정된 디렉토리에서 재귀적으로 모든 파일 찾기
            file_pattern = os.path.join(data_dir, f"**/*.{file_type}")
            files = glob.glob(file_pattern, recursive=True)
            for file in files:
                all_files.append((file, file_type))
        
        return all_files
    
    @staticmethod
    def get_processed_files() -> Set[str]:
        """
        이미 처리된 파일 목록을 DB에서 가져옵니다.
        
        Returns:
            처리된 파일 경로 집합
        """
        return set(EmbeddingFile.objects.values_list('file_path', flat=True))
    
    @staticmethod
    def process_file(file_path: str, file_type: str) -> Dict[str, Any]:
        """
        파일 하나를 처리합니다.
        
        Args:
            file_path: 처리할 파일 경로
            file_type: 파일 타입
            
        Returns:
            처리 결과 정보
        """
        file_result = {
            'file_path': file_path,
            'file_type': file_type,
            'status': '',
            'documents_embedded': 0
        }
        
        try:
            # 1. 파일 확장자 확인
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.csv':
                # 2. SimpleRAG로 CSV 파일 처리
                SimpleRAG.process_file(file_path)
                file_result['status'] = 'success'
                file_result['documents_embedded'] = 1  # 단순화를 위해 1로 설정
                
            elif file_ext == '.txt':
                # 3. SimpleRAG로 TXT 파일 처리
                SimpleRAG.process_file(file_path)  # txt 파일 처리 로직 추가
                file_result['status'] = 'success'
                file_result['documents_embedded'] = 1  # 단순화를 위해 1로 설정
                
            else:
                # 4. 지원하지 않는 파일 형식 처리
                file_result['status'] = 'skipped'
                file_result['message'] = f"지원하지 않는 파일 형식: {file_ext}"
            
            # 5. 처리 성공 시 DB에 기록
            if file_result['status'] == 'success':
                EmbeddingFile.objects.create(
                    file_name=os.path.basename(file_path), 
                    file_path=file_path
                )
            
        except Exception as e:
            # 6. 오류 처리
            file_result['status'] = 'failed'
            file_result['error'] = str(e)
        
        return file_result
    
    @staticmethod
    def process_all_files(
        data_dir: str = 'data', 
        file_types: List[str] = None, 
        force_reprocess: bool = False
    ) -> Dict[str, Any]:
        """
        지정된 디렉토리의 모든 파일을 처리합니다.
        
        Args:
            data_dir: 처리할 파일이 있는 디렉토리 경로
            file_types: 처리할 파일 타입 목록
            force_reprocess: 이미 처리된 파일도 재처리 여부
            
        Returns:
            처리 결과 요약
        """
        # 1. 기본값 설정
        if file_types is None:
            file_types = ['csv', 'txt']  # CSV와 TXT 파일 모두 지원
        
        # 2. 결과 변수 초기화
        results = {
            'total_files_found': 0,
            'new_files_processed': 0,
            'skipped_files': 0,
            'failed_files': 0,
            'processing_time': 0,
            'file_details': []
        }
        
        # 3. 처리할 파일 목록 가져오기
        all_files = EmbeddingService.get_all_files(data_dir, file_types)
        results['total_files_found'] = len(all_files)
        
        # 4. 이미 처리된 파일 목록 가져오기
        processed_files = EmbeddingService.get_processed_files()
        
        # 5. 시작 시간 기록
        start_time = time.time()
        
        # 6. 모든 파일 순회하며 처리
        for file_path, file_type in all_files:
            # 이미 처리된 파일은 건너뛰기
            if file_path in processed_files and not force_reprocess:
                file_result = {
                    'file_path': file_path,
                    'file_type': file_type,
                    'status': 'skipped (already processed)',
                    'documents_embedded': 0
                }
                results['skipped_files'] += 1
                results['file_details'].append(file_result)
                continue
            
            # 파일 처리
            file_result = EmbeddingService.process_file(file_path, file_type)
            results['file_details'].append(file_result)
            
            # 결과 집계
            if file_result['status'] == 'success':
                results['new_files_processed'] += 1
            elif file_result['status'] == 'failed':
                results['failed_files'] += 1
            else:
                results['skipped_files'] += 1
        
        # 7. 처리 시간 계산
        results['processing_time'] = time.time() - start_time
        
        return results 