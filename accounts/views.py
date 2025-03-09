import os
from django.shortcuts import redirect
import requests
from rest_framework import generics, status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from .models import User, Pregnancy
from .serializers import UserSerializer, LoginSerializer, PregnancySerializer, UserUpdateSerializer, ChangePasswordSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as JWTTokenRefreshView
from rest_framework.decorators import action
import logging
from dotenv import load_dotenv
from django.contrib.auth.hashers import get_random_string
from django.http import HttpResponseRedirect, HttpResponse

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


# class FindUsernameView(generics.GenericAPIView):
#     permission_classes = [AllowAny]  # 인증 없이 접근 가능하게 설정
#     serializer_class = FindUsernameSerializer
#
#     def post(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         if serializer.is_valid():
#             email = serializer.validated_data["email"]
#             try:
#                 user = User.objects.get(email=email)
#                 return Response({"username": user.username}, status=status.HTTP_200_OK)
#             except User.DoesNotExist:
#                 return Response({"email": ("해당 이메일로 등록된 계정이 없습니다.")}, status=status.HTTP_400_BAD_REQUEST)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# class ResetPasswordView(generics.GenericAPIView):
#     """비밀번호 찾기 API"""
#     # 비밀번호 찾기 로직 구현

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

        # URL 파라미터로 토큰 전달
        frontend_redirect_uri = "http://localhost:5173/kakao/callback"  # 프론트엔드 콜백 경로
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
        data = {
            'grant_type': 'authorization_code',
            'client_id': os.getenv('NAVER_CLIENT_ID'),  # 네이버 developers에서 발급한 Client ID
            'client_secret': os.getenv('NAVER_CLIENT_SECRET'),  # 네이버 developers에서 발급한 Client Secret
            'code': code,
            'state': state
        }
        print(f"토큰 요청 URL: {token_api_url}")
        print(f"토큰 요청 데이터: {data}")
        print(f"네이버 클라이언트 ID: {os.getenv('NAVER_CLIENT_ID')}")
        print(f"네이버 클라이언트 시크릿: {os.getenv('NAVER_CLIENT_SECRET')[:4]}...")  # 시크릿 일부만 표시
        
        try:
            token_response = requests.post(token_api_url, data=data)
            print(f"토큰 응답 상태 코드: {token_response.status_code}")
            print(f"토큰 응답 내용: {token_response.text}")
            
            token_json = token_response.json()
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

            profile_data = profile_response.json()
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
            is_production = os.environ.get('DJANGO_ENV') == 'production' or request.get_host() != 'localhost:8000'
            
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
            print("======= 네이버 로그인 콜백 종료 =======\n")
            
            return HttpResponseRedirect(redirect_url)
        except Exception as e:
            print(f"❌ 예외 발생: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return Response({'error': f'네이버 로그인 처리 중 오류 발생: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)