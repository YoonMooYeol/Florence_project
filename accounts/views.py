import os
import requests
import logging
import random
import re
from datetime import datetime

from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as JWTTokenRefreshView
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.parsers import MultiPartParser, FormParser

from django.contrib.auth.hashers import get_random_string
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate
from django.conf import settings
from django.core.mail import get_connection, EmailMessage

from .serializers import (
    UserSerializer, LoginSerializer, PregnancySerializer, UserUpdateSerializer, ChangePasswordSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer, FindUsernameSerializer, PasswordResetCheckSerializer,
    PhotoSerializer, FollowUserSerializer
)
from .models import User, Pregnancy, Follow, Photo
from dotenv import load_dotenv

from accounts.utils.email_utils import EmailUtils

# .env 파일 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    """회원가입 API"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class RegisterSendEmailView(APIView):
    """ 회원가입 시 이메일 인증 """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()

        if not email:
            return Response({"success": False, "message": EmailUtils.EMAIL_NO_WRITE_ERROR},
                            status=status.HTTP_400_BAD_REQUEST)

        if not EmailUtils.validate_email(email):
            return Response({"success": False, "message": EmailUtils.EMAIL_INVALID_ERROR},
                            status=status.HTTP_400_BAD_REQUEST)

        code = EmailUtils.generate_verification_code()
        EmailUtils.save_verification_code(email, code)

        try:
            EmailUtils.send_verification_email(email)
        except Exception as e:
            return Response(
                {"success": False, "message": f"이메일 전송 중 오류 발생: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({"success": True, "message": "인증 코드가 전송되었습니다."},
                        status=status.HTTP_200_OK)


class RegisterCheckView(APIView):
    """이메일 인증 코드 확인"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        code = request.data.get("code", "").strip()

        if not email or not code:
            return Response({"success": False, "message": "이메일과 인증 코드를 입력하세요."},
                status=status.HTTP_400_BAD_REQUEST)

        if not EmailUtils.validate_email(email):
            return Response({"success": False, "message": EmailUtils.EMAIL_INVALID_ERROR},
                status=status.HTTP_400_BAD_REQUEST)

        saved_code = EmailUtils.get_verification_code(email)  # 저장된 코드 가져오기

        if not saved_code:
            return Response({"success": False, "message": EmailUtils.CODE_EXPIRED_ERROR},  # 만료된 경우
                status=status.HTTP_400_BAD_REQUEST)

        if saved_code != code:
            return Response({"success": False, "message": EmailUtils.CODE_INVALID_ERROR},  # 코드 불일치
                status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True, "message": "이메일 인증이 완료되었습니다."},
            status=status.HTTP_200_OK)

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


        # 사용자 확인
        user = User.objects.get(email=email)

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

    def send_mail(self, recipient_email, code, html_content=None):
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
            email = EmailMessage(
                subject="[누리달] 💡비밀번호 재설정 인증 코드 안내 💡",
                body=f"안녕하세요\n비밀번호 재설정 인증코드는 [{code}]입니다. 10분 안에 인증을 완료해주세요.",
                from_email=config['HOST_USER'],
                to=[recipient_email],
                connection=connection,
            )
            email.attach_alternative(html_content, "text/html")  # HTML로 변환

            # 이메일 전송
            email.send(fail_silently=False)
            return {"success": True, "message": "이메일이 성공적으로 전송되었습니다."}

        except Exception as e:
            raise Exception(f"이메일 전송 중 오류 발생: {str(e)}")


class PasswordResetConfirmViewSet(viewsets.GenericViewSet):
    """ 비밀번호 재설정 완료 뷰셋 """
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            reset_code = serializer.validated_data['reset_code']
            new_password = serializer.validated_data['new_password']

            # 코드로 사용자 탐색
            user = User.objects.filter(reset_code=reset_code).first()  # 필터로 사용자 찾기
            if not user:
                return Response({"success": False, "message": "잘못된 인증 코드입니다."},
                                status=status.HTTP_400_BAD_REQUEST)

            # 인증 코드 만료 여부 확인
            if not user.check_reset_code(reset_code):
                return Response({"success": False, "message": "인증 코드가 만료되었습니다."},
                                status=status.HTTP_400_BAD_REQUEST)

            # 새 비밀번호 설정
            user.set_password(new_password)
            user.clear_reset_code()  # 인증 코드 초기화

            return Response({"success": True, "message": "비밀번호가 성공적으로 재설정되었습니다."},
                            status=status.HTTP_200_OK)

        except Exception as e:
            # 예외 메시지 로그 출력
            logger.error(f"서버 오류 발생: {str(e)}")
            return Response({"success": False, "message": f"서버 오류: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetCheckViewSet(viewsets.GenericViewSet):
    """ 비밀번호 재설정 코드 확인 뷰셋 """
    permission_classes = [AllowAny]
    serializer_class = PasswordResetCheckSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['reset_code']

        # 코드로 사용자 탐색
        user = User.objects.filter(reset_code=code).first()  # User 객체 조회
        if not user or not user.check_reset_code(code):  # 인증 코드 검증
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


class PregnancyViewSet(viewsets.ModelViewSet):
    serializer_class = PregnancySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Pregnancy.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class KakaoLoginCallbackView(APIView):
    """
    카카오 소셜로그인 리다이렉트 방식:
    카카오에서 code를 받는 콜백 뷰.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # 카카오에서 전달한 code 추출
        code = request.GET.get('code', None)
        if not code:
            return Response({'error': '카카오 인증 code가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # code로 카카오 액세스 토큰 요청
        token_api_url = "https://kauth.kakao.com/oauth/token"
        data = {
            'grant_type': 'authorization_code',
            'client_id': os.getenv('REST_KAKAO_API'),  # 카카오 developers에서 발급한 REST API 키
            'redirect_uri': "http://127.0.0.1:8000/v1/accounts/kakao/callback",  # 디벨로퍼스에 등록된 Redirect URI와 동일
            'code': code
        }
        token_response = requests.post(token_api_url, data=data)
        token_json = token_response.json()
        if 'access_token' not in token_json:
            return Response({'error': '카카오 액세스 토큰을 받지 못했습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        kakao_access_token = token_json['access_token']

        # 액세스 토큰으로 카카오 프로필 요청
        profile_api_url = "https://kapi.kakao.com/v2/user/me"
        headers = {
            "Authorization": f"Bearer {kakao_access_token}"
        }
        profile_response = requests.post(profile_api_url, headers=headers)
        if profile_response.status_code != 200:
            return Response({'error': '카카오 사용자 정보를 가져오지 못했습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        kakao_user = profile_response.json()
        kakao_account = kakao_user.get('kakao_account', {})
        email = kakao_account.get('email', None)

        if not email:
            return Response({'error': '카카오 이메일 정보가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 기존 사용자 찾기
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # 신규 사용자 자동 생성
            username = f"kakao_{kakao_user.get('id')}"
            name = kakao_account.get('profile', {}).get('nickname', '카카오 사용자')
            # 랜덤 비밀번호 생성 (실제 사용되지 않지만 필드는 채워야 함)
            temp_password = get_random_string(length=20)

            user = User.objects.create_user(
                username=username,
                email=email,
                name=name,
                password=temp_password  # 실제로는 사용되지 않음
            )

        # JWT 토큰 생성
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

        # 환경에 따라 적절한 프론트엔드 콜백 URL 사용
        # 환경 변수로 명시적으로 FE_ENV를 설정하거나 DJANGO_ENV를 확인
        # FE_ENV=local 또는 FE_ENV=production으로 설정 가능
        fe_env = os.environ.get('FE_ENV', 'local')  # 기본값은 'local'
        django_env = os.environ.get('DJANGO_ENV', 'development')  # 기본값은 'development'

        # 명시적인 FE_ENV 설정이 없으면 DJANGO_ENV를 기준으로 판단
        is_production = fe_env == 'production' or django_env == 'production'

        # request.get_host()를 출력하여 디버깅에 도움이 되도록 함
        host = request.get_host()
        print(f"Current host: {host}, Environment: {'production' if is_production else 'local'}")

        if is_production:
            frontend_redirect_uri = "https://florence-project-fe.vercel.app/kakao/callback"
        else:
            frontend_redirect_uri = "http://localhost:5173/kakao/callback"

        print(f"Redirecting to: {frontend_redirect_uri}")

        # URL 파라미터로 토큰 전달
        params = {
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'user_id': str(user.user_id),
            'name': user.name,
            'is_pregnant': str(user.is_pregnant).lower()  # 불리언을 문자열로 변환
        }

        # 파라미터를 URL에 추가
        query_string = "&".join([f"{key}={value}" for key, value in params.items()])
        redirect_url = f"{frontend_redirect_uri}?{query_string}"

        return HttpResponseRedirect(redirect_url)


class NaverLoginCallbackView(APIView):
    """
    네이버 소셜로그인 리다이렉트 방식:
    네이버에서 code를 받는 콜백 뷰.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # 디버깅 정보 출력
        print("\n======= 네이버 로그인 콜백 시작 =======")
        print(f"요청 URL: {request.build_absolute_uri()}")
        print(f"요청 헤더: {dict(request.headers)}")
        print(f"요청 GET 파라미터: {dict(request.GET)}")

        # 네이버에서 전달한 code와 state 추출
        code = request.GET.get('code', None)
        state = request.GET.get('state', None)
        print(f"네이버 인증 코드: {code}")
        print(f"네이버 상태 토큰: {state}")

        if not code or not state:
            print("❌ 오류: 네이버 인증 code 또는 state가 없습니다.")
            return Response({'error': '네이버 인증 code 또는 state가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # code로 네이버 액세스 토큰 요청
        token_api_url = "https://nid.naver.com/oauth2.0/token"

        # 환경 변수 확인 및 출력
        naver_client_id = os.getenv('NAVER_CLIENT_ID')
        naver_client_secret = os.getenv('NAVER_CLIENT_SECRET')

        print(f"네이버 클라이언트 ID: {naver_client_id[:4]}..." if naver_client_id else "네이버 클라이언트 ID가 설정되지 않았습니다")
        print(f"네이버 클라이언트 시크릿: {naver_client_secret[:4]}..." if naver_client_secret else "네이버 클라이언트 시크릿이 설정되지 않았습니다")

        if not naver_client_id or not naver_client_secret:
            print("❌ 오류: 네이버 API 키가 설정되지 않았습니다.")
            return Response({'error': '서버 구성 오류: 네이버 API 키가 설정되지 않았습니다.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        data = {
            'grant_type': 'authorization_code',
            'client_id': naver_client_id,
            'client_secret': naver_client_secret,
            'code': code,
            'state': state
        }
        print(f"토큰 요청 URL: {token_api_url}")
        print(f"토큰 요청 데이터: {data}")
        print(f"네이버 클라이언트 ID: {naver_client_id}")
        print(f"네이버 클라이언트 시크릿: {naver_client_secret[:4]}...")  # 시크릿 일부만 표시

        try:
            token_response = requests.post(token_api_url, data=data)
            print(f"토큰 응답 상태 코드: {token_response.status_code}")
            print(f"토큰 응답 내용: {token_response.text}")

            try:
                token_json = token_response.json()
            except Exception as json_error:
                print(f"❌ JSON 파싱 오류: {str(json_error)}, 응답 내용: {token_response.text}")
                return Response({'error': f'네이버 응답을 JSON으로 파싱할 수 없습니다: {str(json_error)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if 'access_token' not in token_json:
                print(f"❌ 오류: 네이버 액세스 토큰을 받지 못했습니다. 응답: {token_json}")
                return Response({'error': '네이버 액세스 토큰을 받지 못했습니다.'}, status=status.HTTP_400_BAD_REQUEST)

            naver_access_token = token_json['access_token']
            print(f"네이버 액세스 토큰: {naver_access_token[:10]}...")

            # 액세스 토큰으로 네이버 프로필 요청
            profile_api_url = "https://openapi.naver.com/v1/nid/me"
            headers = {
                "Authorization": f"Bearer {naver_access_token}"
            }
            print(f"프로필 요청 URL: {profile_api_url}")
            print(f"프로필 요청 헤더: {headers}")

            profile_response = requests.get(profile_api_url, headers=headers)
            print(f"프로필 응답 상태 코드: {profile_response.status_code}")
            print(f"프로필 응답 내용: {profile_response.text}")

            if profile_response.status_code != 200:
                print("❌ 오류: 네이버 사용자 정보를 가져오지 못했습니다.")
                return Response({'error': '네이버 사용자 정보를 가져오지 못했습니다.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                profile_data = profile_response.json()
            except Exception as json_error:
                print(f"❌ 프로필 JSON 파싱 오류: {str(json_error)}, 응답 내용: {profile_response.text}")
                return Response({'error': f'네이버 프로필 응답을 JSON으로 파싱할 수 없습니다: {str(json_error)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            if profile_data.get('resultcode') != '00' or 'response' not in profile_data:
                print(f"❌ 오류: 네이버 사용자 정보가 유효하지 않습니다. 응답: {profile_data}")
                return Response({'error': '네이버 사용자 정보가 유효하지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)

            naver_account = profile_data.get('response', {})
            email = naver_account.get('email')
            print(f"네이버 사용자 정보: {naver_account}")
            print(f"이메일: {email}")

            if not email:
                print("❌ 오류: 네이버 이메일 정보가 없습니다.")
                return Response({'error': '네이버 이메일 정보가 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

            # 사용자 생성 또는 조회
            try:
                # 기존 사용자 찾기
                user = User.objects.get(email=email)
                print(f"✅ 기존 사용자를 찾았습니다: {user.email}, {user.name}")
            except User.DoesNotExist:
                # 신규 사용자 자동 생성
                username = f"naver_{naver_account.get('id', '')}"
                name = naver_account.get('name', '네이버 사용자')
                # 랜덤 비밀번호 생성 (실제 사용되지 않지만 필드는 채워야 함)
                temp_password = get_random_string(length=20)

                print(f"✅ 새 사용자를 생성합니다: {email}, {name}")
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    name=name,
                    password=temp_password  # 실제로는 사용되지 않음
                )
                print(f"✅ 새 사용자가 생성되었습니다: {user.email}, {user.name}")

            # JWT 토큰 생성
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

            print(f"✅ JWT 토큰이 생성되었습니다.")

            # 환경에 따라 적절한 프론트엔드 콜백 URL 사용
            # 환경 변수로 명시적으로 FE_ENV를 설정하거나 DJANGO_ENV를 확인
            # FE_ENV=local 또는 FE_ENV=production으로 설정 가능
            fe_env = os.environ.get('FE_ENV', 'local')  # 기본값은 'local'
            django_env = os.environ.get('DJANGO_ENV', 'development')  # 기본값은 'development'

            # 명시적인 FE_ENV 설정이 없으면 DJANGO_ENV를 기준으로 판단
            is_production = fe_env == 'production' or django_env == 'production'

            # request.get_host()를 출력하여 디버깅에 도움이 되도록 함
            host = request.get_host()
            print(f"Current host: {host}, Environment: {'production' if is_production else 'local'}")

            if is_production:
                frontend_redirect_uri = "https://florence-project-fe.vercel.app/naver/callback"
            else:
                frontend_redirect_uri = "http://localhost:5173/naver/callback"

            print(f"리디렉션 URL: {frontend_redirect_uri}")

            params = {
                'token': str(refresh.access_token),
                'refresh': str(refresh),
                'user_id': str(user.user_id),
                'name': user.name,
                'is_pregnant': str(user.is_pregnant).lower()  # 불리언을 문자열로 변환
            }

            # 파라미터를 URL에 추가
            query_string = "&".join([f"{key}={value}" for key, value in params.items()])
            redirect_url = f"{frontend_redirect_uri}?{query_string}"

            print(f"최종 리디렉션 URL: {redirect_url[:100]}...")
            print("토큰 정보: ", params['token'][:20], "...")
            print("사용자 ID: ", params['user_id'])
            print("======= 네이버 로그인 콜백 종료 =======\n")

            # HttpResponseRedirect로 프론트엔드 페이지로 리디렉션
            return HttpResponseRedirect(redirect_url)
        except Exception as e:
            print(f"❌ 예외 발생: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return Response({'error': f'네이버 로그인 처리 중 오류 발생: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GoogleLoginCallbackView(APIView):
    """
    구글 소셜로그인 리다이렉트 방식:
    구글에서 code를 받는 콜백 뷰.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # 디버깅 정보 출력
        print("\n======= 구글 로그인 콜백 시작 =======")
        print(f"요청 URL: {request.build_absolute_uri()}")
        print(f"요청 헤더: {dict(request.headers)}")
        print(f"요청 GET 파라미터: {dict(request.GET)}")

        # 구글에서 전달한 code 추출
        code = request.GET.get('code', None)

        print(f"구글 인증 코드: {code}")

        if not code:
            print("❌ 오류: 구글 인증 code가 없습니다.")
            # 프론트엔드로 에러 리다이렉션
            frontend_redirect_uri = "http://localhost:5173/google/callback"
            redirect_url = f"{frontend_redirect_uri}?error=인증_코드_없음"
            return HttpResponseRedirect(redirect_url)

        # code로 구글 액세스 토큰 요청
        token_api_url = "https://oauth2.googleapis.com/token"

        # 환경 변수 확인 및 출력
        google_client_id = os.getenv('GOOGLE_CLIENT_ID')
        google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

        print(f"구글 클라이언트 ID: {google_client_id[:10]}..." if google_client_id else "구글 클라이언트 ID가 설정되지 않았습니다")
        print(f"구글 클라이언트 시크릿: {google_client_secret[:4]}..." if google_client_secret else "구글 클라이언트 시크릿이 설정되지 않았습니다")

        if not google_client_id or not google_client_secret:
            print("❌ 오류: 구글 API 키가 설정되지 않았습니다.")
            # 프론트엔드로 에러 리다이렉션
            frontend_redirect_uri = "http://localhost:5173/google/callback"
            redirect_url = f"{frontend_redirect_uri}?error=API_키_설정_없음"
            return HttpResponseRedirect(redirect_url)

        # 리디렉션 URI 설정 - 백엔드 콜백 URL
        redirect_uri = f"http://127.0.0.1:8000/v1/accounts/google/callback"

        data = {
            'grant_type': 'authorization_code',
            'client_id': google_client_id,
            'client_secret': google_client_secret,
            'code': code,
            'redirect_uri': redirect_uri
        }
        print(f"토큰 요청 URL: {token_api_url}")
        print(f"토큰 요청 데이터: {data}")

        try:
            token_response = requests.post(token_api_url, data=data)
            print(f"토큰 응답 상태 코드: {token_response.status_code}")
            print(f"토큰 응답 내용: {token_response.text}")

            try:
                token_json = token_response.json()
            except Exception as json_error:
                print(f"❌ JSON 파싱 오류: {str(json_error)}, 응답 내용: {token_response.text}")
                # 프론트엔드로 에러 리다이렉션
                frontend_redirect_uri = "http://localhost:5173/google/callback"
                redirect_url = f"{frontend_redirect_uri}?error=JSON_파싱_오류"
                return HttpResponseRedirect(redirect_url)

            if 'access_token' not in token_json:
                print(f"❌ 오류: 구글 액세스 토큰을 받지 못했습니다. 응답: {token_json}")
                # 프론트엔드로 에러 리다이렉션
                frontend_redirect_uri = "http://localhost:5173/google/callback"
                redirect_url = f"{frontend_redirect_uri}?error=액세스_토큰_없음"
                return HttpResponseRedirect(redirect_url)

            google_access_token = token_json['access_token']
            print(f"구글 액세스 토큰: {google_access_token[:10]}...")

            # 액세스 토큰으로 구글 프로필 요청
            profile_api_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {
                "Authorization": f"Bearer {google_access_token}"
            }
            print(f"프로필 요청 URL: {profile_api_url}")
            print(f"프로필 요청 헤더: {headers}")

            profile_response = requests.get(profile_api_url, headers=headers)
            print(f"프로필 응답 상태 코드: {profile_response.status_code}")
            print(f"프로필 응답 내용: {profile_response.text}")

            if profile_response.status_code != 200:
                print("❌ 오류: 구글 사용자 정보를 가져오지 못했습니다.")
                # 프론트엔드로 에러 리다이렉션
                frontend_redirect_uri = "http://localhost:5173/google/callback"
                redirect_url = f"{frontend_redirect_uri}?error=사용자_정보_가져오기_실패"
                return HttpResponseRedirect(redirect_url)

            try:
                profile_data = profile_response.json()
            except Exception as json_error:
                print(f"❌ 프로필 JSON 파싱 오류: {str(json_error)}, 응답 내용: {profile_response.text}")
                # 프론트엔드로 에러 리다이렉션
                frontend_redirect_uri = "http://localhost:5173/google/callback"
                redirect_url = f"{frontend_redirect_uri}?error=프로필_JSON_파싱_오류"
                return HttpResponseRedirect(redirect_url)

            # 사용자 정보 추출
            email = profile_data.get('email')
            print(f"구글 사용자 정보: {profile_data}")
            print(f"이메일: {email}")

            if not email:
                print("❌ 오류: 구글 이메일 정보가 없습니다.")
                # 프론트엔드로 에러 리다이렉션
                frontend_redirect_uri = "http://localhost:5173/google/callback"
                redirect_url = f"{frontend_redirect_uri}?error=이메일_정보_없음"
                return HttpResponseRedirect(redirect_url)

            # 사용자 생성 또는 조회
            try:
                # 기존 사용자 찾기
                user = User.objects.get(email=email)
                print(f"✅ 기존 사용자를 찾았습니다: {user.email}, {user.name}")
            except User.DoesNotExist:
                # 신규 사용자 자동 생성
                username = f"google_{profile_data.get('id', '')}"
                name = profile_data.get('name', '구글 사용자')
                # 랜덤 비밀번호 생성 (실제 사용되지 않지만 필드는 채워야 함)
                temp_password = get_random_string(length=20)

                print(f"✅ 새 사용자를 생성합니다: {email}, {name}")
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    name=name,
                    password=temp_password  # 실제로는 사용되지 않음
                )
                print(f"✅ 새 사용자가 생성되었습니다: {user.email}, {user.name}")

            # JWT 토큰 생성
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

            print(f"✅ JWT 토큰이 생성되었습니다.")

            # 환경에 따라 적절한 프론트엔드 콜백 URL 사용
            fe_env = os.environ.get('FE_ENV', 'local')  # 기본값은 'local'
            django_env = os.environ.get('DJANGO_ENV', 'development')  # 기본값은 'development'

            # 명시적인 FE_ENV 설정이 없으면 DJANGO_ENV를 기준으로 판단
            is_production = fe_env == 'production' or django_env == 'production'

            # request.get_host()를 출력하여 디버깅에 도움이 되도록 함
            host = request.get_host()
            print(f"Current host: {host}, Environment: {'production' if is_production else 'local'}")

            if is_production:
                frontend_redirect_uri = "https://florence-project-fe.vercel.app/google/callback"
            else:
                frontend_redirect_uri = "http://localhost:5173/google/callback"

            print(f"리디렉션 URL: {frontend_redirect_uri}")

            params = {
                'token': str(refresh.access_token),
                'refresh': str(refresh),
                'user_id': str(user.user_id),
                'name': user.name,
                'is_pregnant': str(user.is_pregnant).lower(),  # 불리언을 문자열로 변환
                'debug_info': f"host_{host}_time_{str(datetime.now())}"  # 디버깅용 추가 정보
            }

            # 파라미터를 URL에 추가
            query_string = "&".join([f"{key}={value}" for key, value in params.items()])
            redirect_url = f"{frontend_redirect_uri}?{query_string}"

            print(f"최종 리디렉션 URL: {redirect_url[:100]}...")
            print("토큰 정보: ", params['token'][:20], "...")
            print("사용자 ID: ", params['user_id'])
            print("======= 구글 로그인 콜백 종료 =======\n")

            # HttpResponseRedirect로 프론트엔드 페이지로 리디렉션
            return HttpResponseRedirect(redirect_url)
        except Exception as e:
            print(f"❌ 예외 발생: {str(e)}")
            import traceback
            print(traceback.format_exc())

            # 프론트엔드로 에러 리다이렉션
            frontend_redirect_uri = "http://localhost:5173/google/callback"
            redirect_url = f"{frontend_redirect_uri}?error=처리_중_오류_발생"
            return HttpResponseRedirect(redirect_url)


class FindUsernameAPIView(GenericAPIView):
    """ 일반 로그인 사용자 아이디 찾기"""
    permission_classes = [permissions.AllowAny]  # 인증 없이 사용 가능

    serializer_class = FindUsernameSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FollowUnfollowView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FollowUserSerializer

    def get_following_user(self, user_id=None):
        """ user_id를 이용하여 사용자 객체를 가져옴 """
        if user_id:
            try:
                return User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                return None
        return None

    def post(self, request, *args, **kwargs):
        """ 팔로우 기능 """
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "팔로우할 사용자의 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
            
        following_user = self.get_following_user(user_id)
        follower = request.user

        if not following_user:
            return Response({"error": "사용자를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        if follower == following_user:
            return Response({"error": "자기 자신을 팔로우할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        follow, created = Follow.objects.get_or_create(follower=follower, following=following_user)

        if created:
            return Response({"message": f"{following_user.name} 님을 팔로우했습니다.", "status": 1},
                            status=status.HTTP_201_CREATED)
        return Response({"message": "이미 팔로우 중입니다."}, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        """ 언팔로우 기능 """
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "언팔로우할 사용자의 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
            
        following_user = self.get_following_user(user_id)
        follower = request.user

        if not following_user:
            return Response({"error": "사용자를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 팔로우 관계가 존재하는지 확인 후 삭제
        try:
            follow = Follow.objects.get(follower=follower, following=following_user)
            follow.delete()
            return Response({"message": f"{following_user.name} 님을 언팔로우했습니다.", "status": 0},
                            status=status.HTTP_200_OK)
        except Follow.DoesNotExist:
            return Response({"error": "팔로우 관계가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)



class FollowListView(ListAPIView):
    serializer_class = FollowUserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Follow.objects.filter(follower=self.request.user)
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context

class FollowersListView(ListAPIView):
    serializer_class = FollowUserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Follow.objects.filter(following=self.request.user)
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        return context


class RetrieveUserByEmailView(GenericAPIView):
    """ 이메일로 사용자 검색 """
    permission_classes = [permissions.AllowAny]  # [IsAuthenticated] 배포 전 교체

    def get(self, request, *args, **kwargs):
        email = request.query_params.get('email')
        if not email:
            return Response({"detail": "이메일을 작성해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            user_data = {
                'user_id': str(user.user_id),
                'name': user.name
            }
            
            # 현재 사용자가 인증되어 있다면 팔로우 여부 확인
            if request.user.is_authenticated:
                is_following = Follow.objects.filter(
                    follower=request.user,
                    following=user
                ).exists()
                user_data['is_following'] = is_following
            else:
                user_data['is_following'] = False
                
            return Response(user_data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"detail": "사용자를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)


class ProfilePhotoView(APIView):
    def get(self, request, user_id=None):
        """
        특정 사용자의 프로필 사진을 조회할 수 있도록 수정.
        user_id가 제공되지 않으면 현재 사용자의 프로필 사진을 반환.
        """
        if user_id:
            user = get_object_or_404(User, id=user_id)
            photo = get_object_or_404(Photo, user=user)
        else:
            photo = get_object_or_404(Photo, user=request.user)

        serializer = PhotoSerializer(photo)
        return Response(serializer.data)

    def post(self, request):
        """ 현재 사용자에게 프로필 사진이 없을 경우에만 등록 가능 """
        if Photo.objects.filter(user=request.user).exists():
            return Response({"detail": "이미 등록된 사진이 있습니다."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PhotoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """ 현재 사용자의 프로필 사진을 수정 """
        photo = get_object_or_404(Photo, user=request.user)
        serializer = PhotoSerializer(photo, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """ 현재 사용자의 프로필 사진을 삭제 """
        photo = get_object_or_404(Photo, user=request.user)
        photo.delete()
        return Response({"detail": "프로필 사진이 삭제되었습니다."}, status=status.HTTP_204_NO_CONTENT)








