from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    RegisterView, LoginView, TokenRefreshView, PregnancyViewSet, ListUsersView,
    UserDetailView, UpdateUserInfoView, ChangePasswordView, PasswordResetViewSet,
    PasswordResetCheckViewSet, PasswordResetConfirmViewSet, KakaoLoginCallbackView,
    NaverLoginCallbackView, GoogleLoginCallbackView, FindUsernameAPIView, RegisterSendEmailView,
    RegisterCheckView, FollowUnfollowView, FollowListView, FollowersListView, RetrieveUserByEmailView,
    PhotoViewSet, DeleteAccountView
)

pregnancy_router = DefaultRouter()
router = DefaultRouter()
profile_image_router = DefaultRouter()

pregnancy_router.register(r'pregnancies', PregnancyViewSet, basename='pregnancy')
router.register(r'reset_code', PasswordResetViewSet, basename='reset-send-code')
router.register(r'check_code', PasswordResetCheckViewSet, basename='reset-check-code')
router.register(r'confirm_code', PasswordResetConfirmViewSet, basename='reset-confirm')
profile_image_router.register(r'profile-image', PhotoViewSet, basename='photo')


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
    path('kakao/callback', KakaoLoginCallbackView.as_view()),
    path('kakao/callback/', KakaoLoginCallbackView.as_view()),
    path('naver/callback', NaverLoginCallbackView.as_view()),
    path('naver/callback/', NaverLoginCallbackView.as_view()),
    path('google/callback', GoogleLoginCallbackView.as_view(), name='google-callback'),
    path('google/callback/', GoogleLoginCallbackView.as_view()),
    path('apple/callback/', NaverLoginCallbackView.as_view(), name='apple-callback'),  # TODO: 애플 로그인 콜백 구현 필요

    path('send_register/', RegisterSendEmailView.as_view(), name='register-send'),
    path('check_register/', RegisterCheckView.as_view(), name='check-register'),

    path("follow/<str:email>/", FollowUnfollowView.as_view(), name="follow-toggle"),
    path("follow/", FollowUnfollowView.as_view(), name="follow-toggle-id"),  # 추가: user_id로 팔로우/언팔로우 하기 위한 URL
    path('follow-list/following/', FollowListView.as_view(), name='following-list'),
    path('follow-list/followers/', FollowersListView.as_view(), name='followers-list'),

    path('search/', RetrieveUserByEmailView.as_view(), name='search'),  # 이메일로 사용자 검색

    path('users/me/',include(profile_image_router.urls)),

    path('users/me/delete-account/', DeleteAccountView.as_view(), name='delete-account'),

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)