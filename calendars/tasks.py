import logging
from celery import shared_task
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from .views import DailyConversationSummaryViewSet
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

User = get_user_model()
logger = logging.getLogger(__name__)

@shared_task
def auto_summarize_yesterday_conversations():
    """매일 새벽에 전날의 대화를 자동으로 요약하는 태스크"""
    # 어제 날짜 계산
    yesterday = (timezone.now() - timedelta(days=1)).date()
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    
    logger.info(f"전날({yesterday_str}) 대화 자동 요약 시작")
    
    # 모든 활성 사용자에 대해 요약 생성
    users = User.objects.filter(is_active=True)
    success_count = 0
    skipped_count = 0  # 정상적으로 건너뛴 경우 카운트
    error_count = 0
    
    for user in users:
        try:
            # API 요청 모방
            factory = APIRequestFactory()
            request = factory.post(
                '/api/v1/calendars/conversation-summaries/auto_summarize/',
                {'summary_date': yesterday_str},
                format='json'
            )
            
            # 인증을 강제하여 DRF가 user를 "인증됨"으로 인식하도록 함
            force_authenticate(request, user=user)
            
            # ViewSet 실행
            view = DailyConversationSummaryViewSet.as_view({'post': 'auto_summarize'})
            response = view(request)
            
            # 결과 로깅
            if response.status_code == 201:  # HTTP_201_CREATED
                success_count += 1
                logger.info(f"사용자 {user.username}의 {yesterday_str} 대화 요약 생성 완료")
            elif response.status_code == 400 and "요약이 존재합니다" in str(response.data):
                # 이미 요약이 존재하는 경우 - 정상적인 상황
                skipped_count += 1
                logger.info(f"사용자 {user.username}의 {yesterday_str} 대화 요약이 이미 존재함")
            elif response.status_code == 404 and "대화가 없습니다" in str(response.data):
                # 대화가 없는 경우 - 정상적인 상황
                skipped_count += 1
                logger.info(f"사용자 {user.username}의 {yesterday_str} 대화가 없음")
            else:
                # 실제 에러 상황만 에러로 카운트
                error_count += 1
                logger.warning(
                    f"사용자 {user.username}의 {yesterday_str} 대화 요약 생성 실패: "
                    f"상태코드 {response.status_code}, 응답: {response.data}"
                )
                
        except Exception as e:
            error_count += 1
            logger.error(f"사용자 {user.username}의 대화 요약 중 예외 발생: {str(e)}")
    
    result_message = f"전날({yesterday_str}) 대화 자동 요약 완료: 성공 {success_count}건, 건너뜀 {skipped_count}건, 실패 {error_count}건"
    logger.info(result_message)
    
    return result_message

@shared_task
def test_task():
    print("테스트 태스크가 실행되었습니다!")
    return "테스트 성공" 