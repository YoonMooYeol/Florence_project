# config/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime

# Celery 작업 임포트
from calendars.tasks import auto_summarize_yesterday_conversations
from accounts.tasks import update_pregnancy_weeks

logger = logging.getLogger(__name__)

def schedule_celery_task():
    """대화 요약 작업을 Celery 큐에 추가"""
    logger.info(f"APScheduler: {datetime.now()} - 대화 요약 작업을 큐에 추가합니다.")
    auto_summarize_yesterday_conversations.delay()

def schedule_pregnancy_update():
    """임신 주차 업데이트 작업을 Celery 큐에 추가"""
    logger.info(f"APScheduler: {datetime.now()} - 임신 주차 업데이트 작업을 큐에 추가합니다.")
    update_pregnancy_weeks.delay()

# def start():
#     logger.info("APScheduler 시작 시도 중...")
#     scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    
#     # 매일 자정 임신 주차 업데이트 작업 예약
#     scheduler.add_job(
#         schedule_pregnancy_update,  # Celery 작업을 큐에 추가하는 함수
#         trigger=CronTrigger(hour=0, minute=0),
#         id='schedule_pregnancy_update',
#         max_instances=1,
#         replace_existing=True,
#     )
    
#     # 매일 새벽 3시 대화 요약 작업 예약
#     scheduler.add_job(
#         schedule_celery_task,  # Celery 작업을 큐에 추가하는 함수
#         trigger=CronTrigger(hour=13, minute=30),
#         id='schedule_conversation_summary',
#         max_instances=1,
#         replace_existing=True,
#     )
    
#     scheduler.start()
#     logger.info("APScheduler가 성공적으로 시작되었습니다!")


def start():
    logger.info("APScheduler 시작 시도 중...")
    scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
    
    # 테스트용 - 1분마다 실행 (확인용)
    current_minute = datetime.now().minute
    next_minute = (current_minute + 1) % 60
    
    scheduler.add_job(
        schedule_celery_task,
        trigger=CronTrigger(minute=f"*/{next_minute}"),  # 매 next_minute분마다
        id='test_schedule',
        max_instances=1,
        replace_existing=True,
    )
    
    logger.info(f"APScheduler: 대화 요약 작업이 매 {next_minute}분마다 실행되도록 예약되었습니다.")
    scheduler.start()
    logger.info("APScheduler가 성공적으로 시작되었습니다!")