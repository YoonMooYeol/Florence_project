from rest_framework.response import Response
from rest_framework import status, viewsets, generics
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import Http404
import logging

from .utils import process_llm_query
from .models import LLMConversation
from .serializers import QuerySerializer, LLMConversationSerializer, LLMConversationEditSerializer, LLMConversationDeleteSerializer

# User 모델 가져오기
User = get_user_model()

# 로깅 설정
logger = logging.getLogger(__name__)

# 커스텀 get_object_or_404 함수
def custom_get_object_or_404(klass, *args, **kwargs):
    """
    한글 오류 메시지를 반환하는 get_object_or_404 함수
    """
    try:
        return klass.objects.get(*args, **kwargs)
    except klass.DoesNotExist:
        if klass == User:
            raise Http404("사용자를 찾을 수 없습니다.")
        elif klass == LLMConversation:
            raise Http404("대화를 찾을 수 없습니다.")
        else:
            raise Http404("요청한 객체를 찾을 수 없습니다.")

class LLMQueryView(generics.GenericAPIView):
    """LLM 질문 처리 API - 제네릭 뷰 버전"""
    serializer_class = QuerySerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        """LLM 질문 처리"""
        # 요청 데이터 검증
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        # 사용자 조회
        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            # POST 요청이므로 data에서 user_id 가져오기
            user_id = request.data.get('user_id')
            if not user_id:
                return Response({"error": "사용자 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
                
            try:
                user = custom_get_object_or_404(User, user_id=user_id)
            except Http404 as e:
                logger.error(f"사용자 조회 중 오류: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        # 요청 데이터 추출
        query_text = serializer.validated_data['query_text']
        pregnancy_week = serializer.validated_data.get('pregnancy_week')
        
        # 사용자 정보 구성
        user_info = {
            'name': user.name,
            'is_pregnant': user.is_pregnant,
        }
        if pregnancy_week is not None:
            user_info['pregnancy_week'] = pregnancy_week
        
        try:
            # LLM 서비스 호출
            result = process_llm_query(
                user_id=str(user.user_id),
                query_text=query_text,
                user_info=user_info
            )
            
            # 대화 저장
            LLMConversation.objects.create(
                user=user, 
                query=query_text, 
                response=result['response'], 
                user_info=user_info
            )
            
            return Response(result)
        
        except Exception as e:
            logger.error(f"LLM 처리 중 오류: {str(e)}")
            return Response(
                {"error": "요청 처리 중 오류가 발생했습니다."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LLMConversationViewSet(viewsets.ModelViewSet):
    """LLM 대화 관리 API - 뷰셋 버전"""
    serializer_class = LLMConversationSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """현재 사용자의 대화 목록 반환"""
        # 인증된 사용자 확인
        if self.request.user and self.request.user.is_authenticated:
            user = self.request.user
        else:
            # GET 요청이므로 query_params에서 user_id 가져오기
            user_id = self.request.query_params.get('user_id')
            if not user_id:
                return LLMConversation.objects.none()
                
            try:
                user = custom_get_object_or_404(User, user_id=user_id)
            except Http404:
                return LLMConversation.objects.none()
            
        return LLMConversation.objects.filter(user=user).order_by('-created_at')
    
    def get_object(self):
        """대화 객체 조회 - 권한 확인 포함"""
        # 대화 ID 확인
        conversation_id = self.request.query_params.get('conversation_id') # or self.request.query_params.get('index')
        if not conversation_id:
            return None
        
        # 대화 조회
        try:
            conversation = custom_get_object_or_404(LLMConversation, id=conversation_id)
        except Http404 as e:
            self.permission_denied(self.request, message=str(e))
            return None
        
        # 사용자 권한 확인
        if self.request.user and self.request.user.is_authenticated:
            user = self.request.user
        else:
            # HTTP 메서드에 따라 적절한 곳에서 user_id 가져오기
            if self.request.method in ['GET', 'DELETE']:
                user_id = self.request.query_params.get('user_id')
            else:  # POST, PUT, PATCH
                user_id = self.request.data.get('user_id')
                
            if not user_id:
                self.permission_denied(self.request, message="사용자 ID가 필요합니다.")
                return None
                
            try:
                user = custom_get_object_or_404(User, user_id=user_id)
            except Http404 as e:
                self.permission_denied(self.request, message=str(e))
                return None
            
        # 사용자 권한 확인
        if conversation.user and conversation.user != user:
            self.permission_denied(self.request, message="접근 권한이 없습니다.")
            
        return conversation
    
    @action(detail=False, methods=['get'])
    def list_conversations(self, request):
        """사용자의 대화 목록 조회"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'])
    def edit(self, request):
        """대화 수정"""
        # 요청 데이터 검증
        serializer = LLMConversationEditSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        # 대화 조회
        conversation = self.get_object()
        if not conversation:
            return Response({"error": "대화 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 사용자 조회
        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            # PUT 요청이므로 data에서 user_id 가져오기
            user_id = request.data.get('user_id')
            if not user_id:
                return Response({"error": "사용자 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
                
            try:
                user = custom_get_object_or_404(User, user_id=user_id)
            except Http404 as e:
                logger.error(f"사용자 조회 중 오류: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        # 수정할 질문 내용
        new_query = serializer.validated_data.get('query')
        
        try:
            # LLM 서비스 호출
            result = process_llm_query(
                user_id=str(user.user_id),
                query_text=new_query,
                user_info={'name': user.name, 'is_pregnant': user.is_pregnant}
            )
            
            # 대화 업데이트
            conversation.query = new_query
            conversation.response = result['response']
            conversation.save()
            
            return Response(LLMConversationSerializer(conversation).data)
            
        except Exception as e:
            logger.error(f"대화 수정 중 오류: {str(e)}")
            return Response(
                {"error": "대화 수정 중 오류가 발생했습니다."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['delete'])
    def delete(self, request):
        """대화 삭제"""
        # 사용자 조회
        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            # DELETE 요청이므로 query_params에서 user_id 가져오기
            user_id = request.query_params.get('user_id')
            if not user_id:
                return Response({"error": "사용자 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
                
            try:
                user = custom_get_object_or_404(User, user_id=user_id)
            except Http404 as e:
                logger.error(f"사용자 조회 중 오류: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        # 대화 ID 확인
        conversation_id = request.query_params.get('conversation_id') # or request.query_params.get('index')
        
        # 모든 대화 삭제 요청인 경우
        if conversation_id is None:
            count = LLMConversation.objects.filter(user=user).count()
            LLMConversation.objects.filter(user=user).delete()
            return Response({"message": f"{count}개의 대화가 삭제되었습니다."})
        
        # 특정 대화 조회
        conversation = self.get_object()
        if not conversation:
            return Response({"error": "대화를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        
        # 삭제 모드 확인
        serializer = LLMConversationDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        delete_mode = serializer.validated_data.get('delete_mode', 'all')
        
        # 삭제 모드에 따라 처리
        if delete_mode == 'query_only':
            conversation.query = ''
            conversation.save()
            return Response(LLMConversationSerializer(conversation).data)
        else:
            conversation.delete()
            return Response({"message": "대화가 삭제되었습니다."})