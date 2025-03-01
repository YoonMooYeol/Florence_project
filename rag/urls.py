from django.urls import path
from .views import (
    RAGQueryView, RAGAutoEmbedView, RAGViewSet
)
from rest_framework.routers import DefaultRouter
from django.urls import include

# 라우터 설정
router = DefaultRouter()
router.register(r'history', RAGViewSet, basename='rag-history')

urlpatterns = [
    path('', include(router.urls)),
    path('query/', RAGQueryView.as_view(), name='rag-query'),
    path('auto-embed/', RAGAutoEmbedView.as_view(), name='rag-auto-embed'),
]
