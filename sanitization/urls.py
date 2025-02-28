from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 라우터 설정
router = DefaultRouter()
router.register(r'sessions', views.UserSessionViewSet)
router.register(r'interactions', views.InteractionViewSet)
router.register(r'resources', views.PregnancyResourceViewSet)

urlpatterns = [
    # API 엔드포인트
    path('api/', include(router.urls)),
    path('api/llm/', views.MaternalHealthLLMView.as_view(), name='maternal_health_llm'),
    path('api/week/<int:week>/', views.pregnancy_week_info, name='pregnancy_week_info'),
    
    # 웹 인터페이스
    path('', views.index, name='index'),
] 