from typing import Dict, Any, List, Optional
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

class BaseProcessor:
    """
    모든 프로세서의 기본 클래스
    """
    
    def __init__(self):
        # 기본 디렉토리 설정
        self.base_dir = settings.BASE_DIR
        self.temp_dir = getattr(settings, 'RAG_TEMP_DIR', os.path.join(self.base_dir, 'data', 'temp_embeddings'))
        self.db_dir = getattr(settings, 'RAG_DB_DIR', os.path.join(self.base_dir, 'embeddings', 'chroma_db'))
        self.data_dir = getattr(settings, 'RAG_DATA_DIR', os.path.join(self.base_dir, 'data'))
        
        # 디렉토리가 없으면 생성
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.db_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_file_path(self, relative_path: str) -> str:
        """
        상대 경로를 절대 경로로 변환합니다.
        
        Args:
            relative_path: 상대 경로
            
        Returns:
            절대 경로
        """
        if os.path.isabs(relative_path):
            return relative_path
        return os.path.join(self.base_dir, relative_path) 