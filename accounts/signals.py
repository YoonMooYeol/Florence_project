from celery.signals import worker_ready
from .tasks import update_pregnancy_weeks
import logging

logger = logging.getLogger(__name__)

@worker_ready.connect
def trigger_update_on_startup(sender=None, **kwargs):
    """
    Celery worker가 시작될 때 한 번만 임신 주차 업데이트 작업을 실행
    """
    logger.info("Celery worker 시작: 임신 주차 업데이트 작업 예약")
    update_pregnancy_weeks.delay() 