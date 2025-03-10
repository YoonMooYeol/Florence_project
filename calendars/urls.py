from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, DailyConversationSummaryViewSet

router = DefaultRouter()
router.register('events', EventViewSet, basename='event')
router.register('conversation-summaries', DailyConversationSummaryViewSet, basename='conversation-summary')

urlpatterns = [
    path('', include(router.urls)),
]