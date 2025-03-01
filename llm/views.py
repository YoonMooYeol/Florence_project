from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.conf import settings
import logging
import os
from django.http import FileResponse

from .utils import MaternalHealthLLMService
from .models import LLMInteraction
from .serializers import QuerySerializer, ResponseSerializer, LLMInteractionSerializer

# 로깅 설정
logger = logging.getLogger(__name__)

class MaternalHealthLLMView(APIView):
    """
    산모 건강 관련 LLM API 뷰
    
    post(json):
        query_text: 사용자 질문
        user_id: 사용자 ID
        preferences: 사용자 선호도
    response(json):
        response: LLM 응답
        follow_up_questions: 후속 질문 제안
        query_info: 질문 분석 정보
    """
    permission_classes = [AllowAny]  # 인증 없이 접근 가능 (필요에 따라 변경)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm_service = MaternalHealthLLMService()
    
    def post(self, request, format=None):
        """
        사용자 질문을 처리하고 LLM 응답을 반환
        
        """
        # 요청 데이터 검증
        serializer = QuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "잘못된 요청 형식입니다.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 요청 데이터 추출
        validated_data = serializer.validated_data
        user_id = validated_data.get('user_id')
        query_text = validated_data.get('query_text')
        preferences = validated_data.get('preferences', {})
        
        # 사용자 정보 생성 또는 업데이트
        user_info = self._get_or_create_user_info(user_id, preferences)
        
        try:
            # LLM 서비스 호출
            result = self.llm_service.process_query(user_id, query_text, user_info)
            
            # 상호작용 저장
            self._save_interaction(user_id, query_text, result)
            
            # 응답 직렬화
            response_serializer = ResponseSerializer(data={
                'response': result['response'],
                'follow_up_questions': result['follow_up_questions'],
                'query_info': result['query_info']
            })
            
            if response_serializer.is_valid():
                return Response(response_serializer.validated_data, status=status.HTTP_200_OK)
            else:
                logger.error(f"응답 직렬화 오류: {response_serializer.errors}")
                return Response(
                    {"error": "응답 형식 오류", "details": response_serializer.errors},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"LLM 처리 오류: {str(e)}")
            return Response(
                {"error": "서버 오류가 발생했습니다.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_or_create_user_info(self, user_id, preferences):
        """사용자 정보 조회 또는 생성"""
        user_info = {}
        
        if user_id:
            try:
                # 사용자 정보 조회 (Django User 모델 사용 예시)
                user = User.objects.get(id=user_id)
                
                # 사용자 프로필에서 임신 주차 정보 가져오기 (구현 필요)
                # 예: user_info['pregnancy_week'] = user.profile.pregnancy_week
                
                # 사용자 선호도 정보 추가
                user_info.update(preferences)
                
            except User.DoesNotExist:
                logger.warning(f"사용자 ID {user_id}를 찾을 수 없습니다.")
        
        return user_info
    
    def _save_interaction(self, user_id, query_text, result):
        """사용자 상호작용 저장"""
        try:
            # 사용자 객체 조회 (있는 경우)
            user = None
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    pass
            
            # 상호작용 저장
            interaction = LLMInteraction.objects.create(
                user=user,
                query=query_text,
                response=result['response'],
                query_type=result['query_info']['query_type'],
                metadata={
                    'keywords': result['query_info']['keywords'],
                    'follow_up_questions': result['follow_up_questions']
                }
            )
            logger.info(f"상호작용 저장 완료: {interaction.id}")
            
        except Exception as e:
            logger.error(f"상호작용 저장 오류: {str(e)}")


class LLMInteractionViewSet(APIView):
    """
    LLM 상호작용 조회 API
    """
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능
    
    def get(self, request, format=None):
        """
        사용자의 LLM 상호작용 기록 조회
        """
        user_id = request.query_params.get('user_id')
        query_type = request.query_params.get('query_type')
        
        # 쿼리 필터 구성
        filters = {}
        if user_id:
            filters['user_id'] = user_id
        if query_type:
            filters['query_type'] = query_type
        
        # 상호작용 조회
        interactions = LLMInteraction.objects.filter(**filters).order_by('-created_at')
        
        # 페이지네이션 (필요시 구현)
        
        # 직렬화
        serializer = LLMInteractionSerializer(interactions, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)