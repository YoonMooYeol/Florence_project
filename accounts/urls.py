from django.urls import path, include
from rest_framework.routers import DefaultRouter
from streamlit import login

from .views import (RegisterView, LoginView, TokenRefreshView, PregnancyViewSet, ListUsersView,
                    UserDetailView, UpdateUserInfoView, ChangePasswordView, PasswordResetSendCodeView,
                    PasswordResetCheckView
                    )

pregnancy_router = DefaultRouter()
pregnancy_router.register(r'pregnancies', PregnancyViewSet, basename='pregnancy')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),  # 회원가입
    path('login/', include(login.urls)),  # 로그인 관련 API
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # 토큰 갱신

    path('', include(pregnancy_router.urls)),  # 임신 관련 API

    path('users/', ListUsersView.as_view(), name='user-list'),  # 사용자 목록 조회
    path('users/<uuid:user_id>/', UserDetailView.as_view(), name='user-detail'),  # 사용자 상세 조회
    path('users/me/', UpdateUserInfoView.as_view(), name='user-me'),  # 현재 사용자 정보 수정

]