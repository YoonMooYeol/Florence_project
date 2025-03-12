from django.apps import AppConfig


class CalendarsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'calendars'
    
    def ready(self):
        import calendars.tasks  # 태스크 모듈 로드
