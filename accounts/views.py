from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from .models import User
from .serializers import UserSerializer, LoginSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as JWTTokenRefreshView
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

class RegisterView(generics.CreateAPIView):
    """회원가입 API"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class LoginView(APIView):
    """로그인 API"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        # authenticate 함수 사용 (email이 USERNAME_FIELD이므로 email 파라미터로 전달)
        user = authenticate(request, email=email, password=password)
        
        if user:
            # 토큰 생성
            refresh = RefreshToken.for_user(user)
            
            # 토큰에 사용자 정보 추가
            refresh['user_id'] = str(user.user_id)
            refresh['username'] = user.username
            refresh['name'] = user.name
            refresh['email'] = user.email
            refresh['is_pregnant'] = user.is_pregnant
            
            # 액세스 토큰에도 정보 추가
            refresh.access_token['user_id'] = str(user.user_id)
            refresh.access_token['username'] = user.username
            refresh.access_token['name'] = user.name
            refresh.access_token['email'] = user.email
            refresh.access_token['is_pregnant'] = user.is_pregnant
            
            return Response({
                'message': '로그인 성공',
                'user_id': str(user.user_id),
                'name': user.name,
                'is_pregnant': user.is_pregnant,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': '이메일 또는 비밀번호가 올바르지 않습니다.'
            }, status=status.HTTP_401_UNAUTHORIZED)

class TokenRefreshView(JWTTokenRefreshView):
    """토큰 갱신 API
    
    리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급받습니다.
    요청 본문에 refresh 필드에 리프레시 토큰을 포함해야 합니다.
    """
    pass

# class FindUsernameView(generics.GenericAPIView):
#     """아이디 찾기 API"""
#     # 아이디 찾기 로직 구현

# class ResetPasswordView(generics.GenericAPIView):
#     """비밀번호 찾기 API"""
#     # 비밀번호 찾기 로직 구현

# class ChangePasswordView(generics.UpdateAPIView):
#     """비밀번호 수정 API"""
#     # 비밀번호 수정 로직 구현

# class InputMotherInfoView(generics.CreateAPIView):
#     """산모 정보 입력 API"""
#     # 산모 정보 입력 로직 구현

# class UpdateMotherInfoView(generics.UpdateAPIView):
#     """산모 정보 수정 API"""
#     # 산모 정보 수정 로직 구현

# class ListUsersView(generics.ListAPIView):
#     """전체 사용자 조회 API"""
#     queryset = User.objects.all()
#     serializer_class = UserSerializer

# class UserDetailView(generics.RetrieveAPIView):
#     """단일 사용자 정보 조회 API"""
#     queryset = User.objects.all()
#     serializer_class = UserSerializer

# class UpdateUserInfoView(generics.UpdateAPIView):
#     """사용자 정보 변경 API"""
#     queryset = User.objects.all()
#     serializer_class = UserSerializer

# class FollowView(generics.GenericAPIView):
#     """팔로잉/팔로워 기능 API"""
#     # 팔로잉/팔로워 로직 구현