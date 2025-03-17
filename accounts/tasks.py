from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
import logging
from .models import Pregnancy
import math

logger = logging.getLogger(__name__)

@shared_task
def update_pregnancy_weeks():
    """
    모든 사용자의 임신 주차를 자동으로 업데이트하는 태스크
    예시:   
    출산 예정일 3일 전: 40 - 3/7 = 40 - 0.43 = 39.57 → ceil(39.57) = 40주차
    출산 예정일: 40 - 0/7 = 40 → ceil(40) = 40주차
    출산 예정일 3일 후: 40 - (-3/7) = 40 + 0.43 = 40.43 → ceil(40.43) = 41주차
    출산 예정일 10일 후: 40 - (-10/7) = 40 + 1.43 = 41.43 → ceil(41.43) = 42주차
    """
    today = timezone.now().date()
    
    # due_date가 설정된 모든 임신 정보 가져오기
    pregnancies = Pregnancy.objects.filter(due_date__isnull=False)
    
    updated_count = 0
    error_count = 0
    
    for pregnancy in pregnancies:
        try:
            # 출산 예정일과 현재 날짜의 차이 계산
            days_until_due = (pregnancy.due_date - today).days
            
            # 주 단위로 변환 (소수점 유지)
            weeks_until_due = days_until_due / 7  # // 대신 / 사용
            
            # 임신 주차 계산 (올림 처리)
            current_week = math.ceil(40 - weeks_until_due)
            
            # 계산된 주차가 1~42 범위 내에 있는지 확인
            if current_week < 1:
                current_week = 1
            elif current_week > 42:
                current_week = 42
                
            # 변경사항이 있을 때만 업데이트
            if pregnancy.current_week != current_week:
                pregnancy.current_week = current_week
                pregnancy.save(update_fields=['current_week'])
                updated_count += 1
            
        except Exception as e:
            logger.error(f"임신 주차 업데이트 중 오류 발생 (임신 ID: {pregnancy.pregnancy_id}): {str(e)}")
            error_count += 1
    
    result_message = f"임신 주차 자동 업데이트 완료: 총 {len(pregnancies)}건 중 {updated_count}건 업데이트, {error_count}건 오류"
    logger.info(result_message)
    return result_message
