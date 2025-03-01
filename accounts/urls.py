from django.urls import path
from .views import RegisterView, LoginView, TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),  # 회원가입
    path('login/', LoginView.as_view(), name='login'),  # 로그인
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # 토큰 갱신
]