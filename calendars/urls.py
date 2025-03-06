from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet

router = DefaultRouter()
router.register('events', EventViewSet, basename='event')

urlpatterns = [
    path('', include(router.urls)),
]