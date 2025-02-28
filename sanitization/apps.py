from django.apps import AppConfig


class SanitizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sanitization"
    verbose_name = "산모 대상 LLM 서비스"

    def ready(self):
        """앱 초기화 시 실행되는 메서드"""
        # 로깅 설정
        import logging
        logger = logging.getLogger(__name__)
        logger.info("산모 대상 LLM 서비스 앱이 초기화되었습니다.")
