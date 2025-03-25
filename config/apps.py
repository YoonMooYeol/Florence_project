# config/apps.py
from django.apps import AppConfig

class ConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'
    
    def ready(self):
        import logging
        logger = logging.getLogger(__name__)
        logger.info("ConfigConfig.ready() 메서드 호출됨")
        
        # 개발 서버에서 실행될 때 두 번 로드되는 것 방지
        import os
        if os.environ.get('RUN_MAIN') != 'true':
            logger.info("스케줄러 시작 조건 충족")
            try:
                from . import scheduler
                scheduler.start()
                logger.info("스케줄러 시작 완료")
            except ImportError as e:
                logger.error(f"스케줄러 임포트 오류: {e}")
            except Exception as e:
                logger.error(f"스케줄러 시작 중 오류 발생: {e}") 