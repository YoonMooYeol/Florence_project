
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RegisterView, LoginView, TokenRefreshView, PregnancyViewSet, ListUsersView,
    UserDetailView, UpdateUserInfoView, ChangePasswordView, PasswordResetViewSet,
    PasswordResetCheckViewSet, PasswordResetConfirmViewSet
                    )


pregnancy_router = DefaultRouter()
router = DefaultRouter()

pregnancy_router.register(r'pregnancies', PregnancyViewSet, basename='pregnancy')
router.register(r'reset_code', PasswordResetViewSet, basename='reset-send-code')
router.register(r'check_code', PasswordResetCheckViewSet, basename='reset-check-code')
router.register(r'confirm_code', PasswordResetConfirmViewSet, basename='reset-confirm')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),  # 회원가입
    path('login/', LoginView.as_view(), name='login'),  # 로그인
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # 토큰 갱신

    path('', include(pregnancy_router.urls)),  # 임신 관련 API

    path('users/', ListUsersView.as_view(), name='user-list'),  # 사용자 목록 조회
    path('users/<uuid:user_id>/', UserDetailView.as_view(), name='user-detail'),  # 사용자 상세 조회
    path('users/me/', UpdateUserInfoView.as_view(), name='user-me'),  # 현재 사용자 정보 수정
    path('users/me/change-password/', ChangePasswordView.as_view(), name='change-password'), # 현재 사용자 비밀번호 변경

    path('', include(router.urls)),

]