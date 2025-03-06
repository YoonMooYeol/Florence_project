from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 라우터 설정
router = DefaultRouter()
router.register(r'files', views.EmbeddingFileViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('auto-embed/', views.RAGAutoEmbedView.as_view(), name='auto-embed'),
    path('manual-embed/', views.RAGManualEmbedView.as_view(), name='manual-embed'),
    path('pregnancy-info/', views.PregnancyInfoView.as_view(), name='pregnancy-info'),
]
