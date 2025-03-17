
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RegisterView, LoginView, TokenRefreshView, PregnancyViewSet, ListUsersView,
    UserDetailView, UpdateUserInfoView, ChangePasswordView, PasswordResetViewSet,
    PasswordResetCheckViewSet, PasswordResetConfirmViewSet, KakaoLoginCallbackView,
    NaverLoginCallbackView, GoogleLoginCallbackView, FindUsernameAPIView, RegisterSendEmailView,
    RegisterCheckView, FollowUnfollowView, RetrieveUserByEmailView, PhotoViewSet, DiaryPhotoViewSet,
    FollowListView, FollowersListView
)

pregnancy_router = DefaultRouter()
router = DefaultRouter()
photo_profile_router = DefaultRouter()
photo_diary_router = DefaultRouter()

pregnancy_router.register(r'pregnancies', PregnancyViewSet, basename='pregnancy')
router.register(r'reset_code', PasswordResetViewSet, basename='reset-send-code')
router.register(r'check_code', PasswordResetCheckViewSet, basename='reset-check-code')
router.register(r'confirm_code', PasswordResetConfirmViewSet, basename='reset-confirm')
photo_profile_router.register(r'profile', PhotoViewSet, basename='photo-profile')
photo_diary_router.register(r'diary', DiaryPhotoViewSet, basename='photo-diary')


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),  # 회원가입
    path('login/', LoginView.as_view(), name='login'),  # 로그인
    path('find_username/', FindUsernameAPIView.as_view(), name='find-username'),    # 아이디 찾기
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # 토큰 갱신

    path('', include(pregnancy_router.urls)),  # 임신 관련 API

    path('users/', ListUsersView.as_view(), name='user-list'),  # 사용자 목록 조회
    path('users/<uuid:user_id>/', UserDetailView.as_view(), name='user-detail'),  # 사용자 상세 조회
    path('users/me/', UpdateUserInfoView.as_view(), name='user-me'),  # 현재 사용자 정보 수정
    path('users/me/change-password/', ChangePasswordView.as_view(), name='change-password'), # 현재 사용자 비밀번호 변경

    path('', include(router.urls)), # 이메일 인증 및 비밀번호 재설정

    # 소셜 로그인 콜백 URL
    path('kakao/callback/', KakaoLoginCallbackView.as_view(), name='kakao-callback'),
    path('naver/callback/', NaverLoginCallbackView.as_view(), name='naver-callback'),
    path('google/callback/', GoogleLoginCallbackView.as_view(), name='google-callback'),
    path('apple/callback/', NaverLoginCallbackView.as_view(), name='apple-callback'),  # TODO: 애플 로그인 콜백 구현 필요

    path('send_register/', RegisterSendEmailView.as_view(), name='register-send'),
    path('check_register/', RegisterCheckView.as_view(), name='check-register'),

    path("follow/<str:email>/", FollowUnfollowView.as_view(), name="follow-toggle"),
    path('follow/following/', FollowListView.as_view(), name='following-list'),
    path('follow/followers/', FollowersListView.as_view(), name='followers-list'),

    path('search/', RetrieveUserByEmailView.as_view(), name='search'),

    path('users/photos/', include(photo_profile_router.urls), name='photos-profile'),
    path('users/photos/', include(photo_diary_router.urls), name='photos-diary'),


]