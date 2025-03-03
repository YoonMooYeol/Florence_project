from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RagConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rag"
    verbose_name = _('검색 증강 생성')

    def ready(self):
        """앱이 시작될 때 실행되는 코드"""
        # 필요한 초기화 코드 추가
        pass
