from django.urls import path
from . import views

app_name = 'llm'

urlpatterns = [
    # API 엔드포인트
    path('api/maternal-health-llm/', views.MaternalHealthLLMView.as_view(), name='maternal_health_llm_api'),
    path('api/interactions/', views.LLMInteractionViewSet.as_view(), name='llm_interactions_api'),
] 