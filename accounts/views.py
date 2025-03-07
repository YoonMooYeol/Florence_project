import logging
import random
import re

from rest_framework import generics, status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as JWTTokenRefreshView


from django.contrib.auth import authenticate
from django.conf import settings
from django.core.mail import EmailMessage, get_connection

from .serializers import(
    UserSerializer, LoginSerializer, PregnancySerializer, UserUpdateSerializer, ChangePasswordSerializer,
    PasswordResetSerializer, PasswordResetCheckSerializer
)
from .models import User, Pregnancy
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()






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
    """ 토큰 갱신 API """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "refresh 토큰이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
        serializer.is_valid(raise_exception=True)

        return Response(
            {
                "access": serializer.validated_data["access"]
            },
            status=status.HTTP_200_OK
        )


class PasswordResetViewSet(viewsets.GenericViewSet):
    """ 비밀번호 재설정 코드 전송 뷰셋 """
    permission_classes = [AllowAny]
    serializer_class = PasswordResetSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        print(f"Received email: {email}")

        # 사용자 확인
        user = User.objects.filter(email__iexact=email).first()
        print(f"Found users: {user}")
        if not user:
            return Response({"success": False, "message": "해당 이메일의 사용자가 없습니다."},
                            status=status.HTTP_404_NOT_FOUND)

        # 랜덤 코드 생성
        code = str(random.randint(100000, 999999))
        user.send_reset_code(code, end_minutes=10)

        # 이메일 전송
        try:
            self.send_mail(email, code)
            return Response({"success": True, "message": "인증 코드 전송 성공"},
                            status=status.HTTP_200_OK)
        except ValueError:
            return Response({"success": False, "message": "정확한 이메일 주소를 입력해 주세요."},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"success": False, "message": f"이메일 전송 중 오류가 발생했습니다: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def send_mail(self, recipient_email, code):
        """ 이메일 전송 """
        # 이메일 주소 형식 확인
        if not re.match(r"[^@]+@[^@]+\.[^@]+", recipient_email):
            raise ValueError("정확한 이메일 주소를 입력해 주세요.")

        domain = recipient_email.split('@')[-1].lower()
        config = settings.SMTP_CONFIG.get(domain, settings.EMAIL_CONFIG)

        try:
            connection = get_connection(

            # 이메일 설정을 settings에서 가져오기
                host=config['HOST'],
                use_tls=config['USE_TLS'],
                port=config['PORT'],
                username=config['HOST_USER'],
                password=config['HOST_PASSWORD'],

            )
            email_message = EmailMessage(
                subject="[Touch_Moms] 비밀번호 재설정 코드 안내",
                body=f"안녕하세요\n비밀번호 재설정 인증코드는 [{code}]입니다. 10분 안에 인증을 완료해주세요.",
                from_email=config['HOST_USER'],
                to=[recipient_email],
                connection=connection
            )

            email_message.send(fail_silently=False)

        except Exception as e:
            logger.error(f"이메일 전송 실패: {str(e)}")
            raise Exception(f"이메일 전송 실패: {str(e)}")


class PasswordResetConfirmViewSet(viewsets.GenericViewSet):
    """ 비밀번호 재설정 완료 뷰셋 """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['code']
        new_password = serializer.validated_data['new_password']

        # 코드로 사용자 탐색
        user = User.objects.filter(reset_code=code).first()
        if not user or not user.check_reset_code(code):
            return Response({"success": False, "message": "만료되었거나 잘못된 코드입니다."},
                            status=status.HTTP_400_BAD_REQUEST)

        # 새 비밀번호 설정
        user.set_password(new_password)
        user.clear_reset_code()

        return Response({"success": True, "message": "비밀번호가 성공적으로 재설정되었습니다."},
                        status=status.HTTP_200_OK)

class PasswordResetCheckViewSet(viewsets.GenericViewSet):
    """ 비밀번호 재설정 코드 확인 뷰셋 """
    permission_classes = [AllowAny]
    serializer_class = PasswordResetCheckSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['code']

        # 코드로 사용자 탐색
        user = User.objects.filter(reset_code=code).first()
        if not user or not user.check_reset_code(code):
            return Response({"success": False, "message": "만료되었거나 잘못된 코드입니다."},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True, "message": "인증 완료"},
                        status=status.HTTP_200_OK)


class ChangePasswordView(generics.UpdateAPIView):
    """비밀번호 수정 API"""
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def put(self, request, *args, **kwargs):  # post 대신 put 사용
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # 현재 비밀번호 확인
            if not user.check_password(serializer.validated_data['current_password']):
                return Response(
                    {"current_password": "현재 비밀번호가 올바르지 않습니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 새 비밀번호로 변경
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({
                "message": "비밀번호가 성공적으로 변경되었습니다."
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListUsersView(generics.ListAPIView):
    """전체 사용자 조회 API"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class UserDetailView(generics.RetrieveAPIView):
    """단일 사용자 정보 조회 API"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'user_id'  # UUID 필드를 사용하여 조회

class UpdateUserInfoView(generics.RetrieveUpdateAPIView):
    """사용자 정보 조회/변경 API"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        # 현재 로그인한 사용자의 정보만 수정 가능
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer  # 수정용 시리얼라이저 (비밀번호 필드 제외)
        return UserSerializer  # 조회용 시리얼라이저
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'message': '사용자 정보가 성공적으로 수정되었습니다.',
            'data': serializer.data
        })

# class FollowView(generics.GenericAPIView):
#     """팔로잉/팔로워 기능 API"""
#     # 팔로잉/팔로워 로직 구현

class PregnancyViewSet(viewsets.ModelViewSet):
    serializer_class = PregnancySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Pregnancy.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # @action(detail=False, methods=['get'])
    # def current_pregnancy(self, request):
    #     """현재 진행 중인 임신 정보를 가져옵니다."""
    #     pregnancy = self.get_queryset().first()
    #     if pregnancy:
    #         serializer = self.get_serializer(pregnancy)
    #         return Response(serializer.data)
    #     return Response(
    #         {"message": "등록된 임신 정보가 없습니다."},
    #         status=status.HTTP_404_NOT_FOUND
    #     )

# class FindUsernameView(generics.GenericAPIView):
#     """ 아이디 찾기 """
