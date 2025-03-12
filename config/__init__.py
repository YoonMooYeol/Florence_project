# Celery 앱을 이 파일에서 import하여 Django가 시작될 때 항상 로드되도록 함
from .celery import app as celery_app

__all__ = ('celery_app',)
