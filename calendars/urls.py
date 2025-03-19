from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, DailyConversationSummaryViewSet, BabyDiaryViewSet, BabyDiaryPhotoView

router = DefaultRouter()


router.register('events', EventViewSet, basename='event')
router.register('conversation-summaries', DailyConversationSummaryViewSet, basename='conversation-summary')
router.register('baby-diaries', BabyDiaryViewSet, basename='baby-diary')

urlpatterns = [
    path('', include(router.urls)),
    path('baby-diaries/<uuid:diary_id>/photo/', BabyDiaryPhotoView.as_view(),
                                                            name='baby_diary_photo_list'),  # 모든 사진 조회 및 추가
    path('baby-diaries/<uuid:diary_id>/photo/<uuid:pk>/', BabyDiaryPhotoView.as_view(),
                                                            name='baby_diary_photo_detail'),  # 특정 사진 조회, 수정, 삭제
    path('baby-diaries/<uuid:diary_id>/diary/', BabyDiaryViewSet.as_view({
        'get': 'retrieve_by_id', 
        'put': 'update_by_id', 
        'patch': 'partial_update_by_id', 
        'delete': 'destroy_by_id'
    }), name='baby_diary_by_id'),
    path('baby-diaries/pregnancy/<uuid:pregnancy_id>/', BabyDiaryViewSet.as_view({
        'post': 'create',  # pregnancy_id로 일기 생성
        'patch': 'partial_update',  # pregnancy_id로 일기 부분 수정
    })),
    path('baby-diaries/pregnancy/<uuid:pregnancy_id>/<str:diary_date>/',
         BabyDiaryViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),
]