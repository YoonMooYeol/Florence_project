import os
from celery import Celery

# Django 설정 모듈을 기본값으로 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Celery 앱 생성
app = Celery('config')

# 설정 모듈에서 Celery 관련 설정값을 가져옴
# namespace='CELERY'는 모든 셀러리 관련 설정키가 'CELERY_' 로 시작해야 함을 의미
app.config_from_object('django.conf:settings', namespace='CELERY')

# 등록된 Django 앱 설정에서 task 모듈을 자동으로 탐색
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 