from celery.signals import worker_ready
from .tasks import update_pregnancy_weeks
import logging
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os
from django.conf import settings
from .models import Photo

logger = logging.getLogger(__name__)

@worker_ready.connect
def trigger_update_on_startup(sender=None, **kwargs):
    """
    Celery worker가 시작될 때 한 번만 임신 주차 업데이트 작업을 실행
    """
    logger.info("Celery worker 시작: 임신 주차 업데이트 작업 예약")
    update_pregnancy_weeks.delay()


@receiver(post_delete, sender=Photo)
def delete_photo_file(sender, instance, **kwargs):
    if instance.image:
        file_path = instance.image.path
        if os.path.exists(file_path):
            os.remove(file_path)