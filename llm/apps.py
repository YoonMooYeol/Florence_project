from django.apps import AppConfig
import os
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

class LlmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "llm"
    verbose_name = "LLM 서비스"
    
    def ready(self):
        """앱 초기화 시 실행되는 코드"""
        # OpenAI API 키가 설정되어 있는지 확인
        if not os.environ.get('OPENAI_API_KEY'):
            logger.warning('OPENAI_API_KEY가 설정되지 않았습니다. LLM 기능이 작동하지 않을 수 있습니다.')

        # 벡터 스토어 ID가 설정되어 있는지 확인
        if not os.environ.get('VECTOR_STORE_ID'):
            logger.warning('VECTOR_STORE_ID가 설정되지 않았습니다. 벡터 검색 기능이 제한될 수 있습니다.')
            
        # 사용자 정의 에이전트 패키지가 설치되어 있는지 확인
        try:
            import agents
            logger.info('OpenAI 에이전트 패키지가 성공적으로 로드되었습니다.')
        except ImportError:
            logger.error('OpenAI 에이전트 패키지를 가져올 수 없습니다. "agents" 패키지가 설치되었는지 확인하세요.')
            
        logger.info('LLM 서비스가 초기화되었습니다.')
