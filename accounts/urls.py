from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, LoginView, TokenRefreshView, PregnancyViewSet, FindUsernameView

pregnancy_router = DefaultRouter()
pregnancy_router.register(r'pregnancies', PregnancyViewSet, basename='pregnancy')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),  # 회원가입
    path('login/', LoginView.as_view(), name='login'),  # 로그인
    path("find_id/", FindUsernameView.as_view(), name="find-id"),   # 아이디 찾기
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # 토큰 갱신
    path('', include(pregnancy_router.urls)),  # 임신 관련 API
]