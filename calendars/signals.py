from celery.signals import worker_ready
from .tasks import auto_summarize_yesterday_conversations
import logging

logger = logging.getLogger(__name__)

@worker_ready.connect
def trigger_summarize_on_startup(sender=None, **kwargs):
    """
    Celery worker가 시작될 때 한 번만 대화 자동 요약 작업을 실행
    """
    logger.info("Celery worker 시작: 대화 자동 요약 작업 예약")
    auto_summarize_yesterday_conversations.delay() 