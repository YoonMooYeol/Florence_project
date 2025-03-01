from django.apps import AppConfig


class LlmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "llm"
    verbose_name = "LLM 서비스"
    
    def ready(self):
        """앱 초기화 시 실행되는 코드"""
        # 필요한 초기화 코드가 있다면 여기에 추가
        pass
