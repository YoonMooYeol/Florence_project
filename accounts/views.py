from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny  # 인증 없이 접근 가능하도록 설정
from .models import User
from .serializers import UserSerializer, LoginSerializer
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as JWTTokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError
import uuid
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

class RegisterView(generics.CreateAPIView):
    """회원가입 API"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]  # 인증 없이 접근 가능하도록 설정

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class LoginView(generics.GenericAPIView):
    """로그인 API"""
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]  # 인증 없이 접근 가능하도록 설정
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        logger.debug(f"로그인 시도: 이메일={email}")

        try:
            user = User.objects.get(email=email)
            logger.debug(f"사용자 조회 성공: {user.name}, UUID={user.user_id}")
            
            if check_password(password, user.password):
                # 직접 토큰 생성
                refresh_token = self._generate_refresh_token(user)
                access_token = self._generate_access_token(user, refresh_token)
                
                # 응답 데이터 준비
                response_data = {
                    'message': '로그인 성공',
                    'user_id': str(user.user_id),
                    'name': user.name,
                    'is_pregnant': user.is_pregnant,
                    'tokens': {
                        'refresh': str(refresh_token),
                        'access': str(access_token),
                    }
                }
                
                logger.debug(f"로그인 성공: user_id={response_data['user_id']}")
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                logger.warning(f"비밀번호 불일치: 이메일={email}")
                return Response({'error': '비밀번호가 일치하지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.warning(f"사용자 없음: 이메일={email}")
            return Response({'error': '사용자를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
    
    def _generate_refresh_token(self, user):
        """리프레시 토큰 생성"""
        refresh_token = RefreshToken()
        
        # 토큰에 사용자 정보 추가
        user_id_str = str(user.user_id)
        refresh_token['user_id'] = user_id_str
        refresh_token['name'] = user.name
        refresh_token['email'] = user.email
        refresh_token['is_pregnant'] = user.is_pregnant
        refresh_token['token_type'] = 'refresh'
        
        logger.debug(f"리프레시 토큰 생성: user_id={user_id_str}")
        return refresh_token
    
    def _generate_access_token(self, user, refresh_token):
        """액세스 토큰 생성"""
        access_token = refresh_token.access_token
        
        # 토큰에 사용자 정보 추가
        user_id_str = str(user.user_id)
        access_token['user_id'] = user_id_str
        access_token['name'] = user.name
        access_token['email'] = user.email
        access_token['is_pregnant'] = user.is_pregnant
        access_token['token_type'] = 'access'
        
        logger.debug(f"액세스 토큰 생성: user_id={user_id_str}")
        return access_token

class TokenRefreshView(generics.GenericAPIView):
    """토큰 갱신 API
    
    리프레시 토큰을 사용하여 새로운 액세스 토큰을 발급받습니다.
    요청 본문에 refresh 필드에 리프레시 토큰을 포함해야 합니다.
    """
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            logger.warning("리프레시 토큰이 제공되지 않았습니다.")
            return Response(
                {"error": "리프레시 토큰이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 리프레시 토큰 검증
            token = RefreshToken(refresh_token)
            
            # 토큰에서 사용자 정보 추출
            user_id = token.get('user_id')
            logger.debug(f"토큰에서 추출한 user_id: {user_id}")
            
            if not user_id:
                logger.warning("토큰에 user_id가 없습니다.")
                return Response(
                    {"error": "유효하지 않은 토큰입니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # 사용자 조회
                user = User.objects.get(user_id=uuid.UUID(user_id))
                logger.debug(f"사용자 조회 성공: {user.name}, UUID={user.user_id}")
                
                # 새로운 액세스 토큰 생성
                access_token = token.access_token
                
                # 사용자 정보 추가
                user_id_str = str(user.user_id)
                access_token['user_id'] = user_id_str
                access_token['name'] = user.name
                access_token['email'] = user.email
                access_token['is_pregnant'] = user.is_pregnant
                access_token['token_type'] = 'access'
                
                logger.debug(f"새 액세스 토큰 생성: user_id={user_id_str}")
                
                return Response({
                    'access': str(access_token)
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                logger.warning(f"사용자를 찾을 수 없습니다: user_id={user_id}")
                return Response(
                    {"error": "사용자를 찾을 수 없습니다."},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except TokenError as e:
            logger.warning(f"토큰 오류: {str(e)}")
            return Response(
                {"error": "유효하지 않은 토큰입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

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