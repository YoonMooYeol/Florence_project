from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny  # 인증 없이 접근 가능하도록 설정
from .models import User
from .serializers import UserSerializer, LoginSerializer
from django.contrib.auth.hashers import check_password

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

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(email=email)
            if check_password(password, user.password_hash):
                return Response({'message': '로그인 성공', 'user_id': str(user.user_id)}, status=status.HTTP_200_OK)
            else:
                return Response({'error': '비밀번호가 일치하지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': '사용자를 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        

# class TokenRefreshView(generics.GenericAPIView):
#     """토큰 갱신 API"""
#     # 토큰 갱신 로직 구현

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