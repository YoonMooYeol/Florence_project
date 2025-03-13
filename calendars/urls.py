from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, DailyConversationSummaryViewSet, BabyDiaryViewSet

router = DefaultRouter()
router.register('events', EventViewSet, basename='event')
router.register('conversation-summaries', DailyConversationSummaryViewSet, basename='conversation-summary')
router.register('baby-diaries', BabyDiaryViewSet, basename='baby-diary')

urlpatterns = [
    path('', include(router.urls)),
]