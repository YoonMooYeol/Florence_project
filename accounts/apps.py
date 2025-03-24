from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        import accounts.tasks  # 태스크 모듈 로드
        import accounts.signals  # 시그널 모듈 로드

