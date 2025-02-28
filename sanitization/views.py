import logging
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserSession, Interaction, PregnancyResource
from .serializers import (
    UserSessionSerializer, InteractionSerializer, 
    PregnancyResourceSerializer, QuerySerializer, ResponseSerializer
)
from .utils import MaternalHealthLLMService

# 로깅 설정
logger = logging.getLogger(__name__)

class UserSessionViewSet(viewsets.ModelViewSet):
    """사용자 세션 뷰셋"""
    queryset = UserSession.objects.all()
    serializer_class = UserSessionSerializer


class InteractionViewSet(viewsets.ModelViewSet):
    """사용자 상호작용 뷰셋"""
    queryset = Interaction.objects.all()
    serializer_class = InteractionSerializer
    filterset_fields = ['session', 'query_type']
    
    def get_queryset(self):
        """특정 세션의 상호작용만 필터링"""
        queryset = super().get_queryset()
        session_id = self.request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        return queryset


class PregnancyResourceViewSet(viewsets.ModelViewSet):
    """임신 리소스 뷰셋"""
    queryset = PregnancyResource.objects.all()
    serializer_class = PregnancyResourceSerializer
    filterset_fields = ['week']


class MaternalHealthLLMView(APIView):
    """산모 대상 LLM 서비스 API 뷰"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.llm_service = MaternalHealthLLMService()
    
    def post(self, request, format=None):
        """사용자 질문 처리 및 응답 생성"""
        serializer = QuerySerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {"error": "잘못된 요청 형식", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_id = serializer.validated_data['user_id']
        query_text = serializer.validated_data['query_text']
        pregnancy_week = serializer.validated_data.get('pregnancy_week')
        preferences = serializer.validated_data.get('preferences', {})
        
        # 1. 사용자 세션 조회 또는 생성
        user_session, created = UserSession.objects.get_or_create(
            user_id=user_id,
            defaults={'preferences': preferences}
        )
        
        # 2. 임신 주차 업데이트 (제공된 경우)
        if pregnancy_week is not None:
            user_session.pregnancy_week = pregnancy_week
            user_session.save()
        
        # 3. 사용자 정보 구성
        user_info = {
            'pregnancy_week': user_session.pregnancy_week,
            'preferences': user_session.preferences
        }
        
        # 4. LLM 서비스 호출
        try:
            result = self.llm_service.process_query(user_id, query_text, user_info)
            
            # 5. 상호작용 저장
            interaction = Interaction.objects.create(
                session=user_session,
                query=query_text,
                response=result['response'],
                query_type=result['query_info']['query_type'],
                metadata={
                    'query_info': result['query_info'],
                    'follow_up_questions': result['follow_up_questions']
                }
            )
            
            # 6. 응답 직렬화
            response_serializer = ResponseSerializer(result)
            return Response(response_serializer.data)
            
        except Exception as e:
            logger.error(f"LLM 서비스 처리 오류: {str(e)}", exc_info=True)
            return Response(
                {"error": "서비스 처리 오류", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
def pregnancy_week_info(request, week):
    """특정 임신 주차 정보 조회 API"""
    try:
        # 캐시된 리소스 조회
        resource = PregnancyResource.objects.filter(week=week).first()
        
        if resource:
            # 캐시된 데이터 반환
            return Response({
                'week': resource.week,
                'label': resource.label,
                'data': resource.data
            })
        
        # 캐시에 없으면 API 조회
        llm_service = MaternalHealthLLMService()
        api_manager = llm_service.api_manager
        
        week_info = api_manager.get_pregnancy_week_info(week)
        
        if not week_info or 'error' in week_info:
            return Response(
                {"error": "임신 주차 정보를 찾을 수 없습니다", "details": week_info.get('error', '')},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 리소스 URI와 레이블 추출
        resource_uri = week_info.get('resource_uri', '')
        resource_label = "임신 " + str(week) + "주차"
        
        if 'summary' in week_info and 'resource_label' in week_info['summary']:
            resource_label = week_info['summary']['resource_label']
        
        # 캐시에 저장
        PregnancyResource.objects.create(
            resource_uri=resource_uri,
            week=week,
            label=resource_label,
            data=week_info
        )
        
        return Response({
            'week': week,
            'label': resource_label,
            'data': week_info
        })
        
    except Exception as e:
        logger.error(f"임신 주차 정보 조회 오류: {str(e)}", exc_info=True)
        return Response(
            {"error": "서비스 처리 오류", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def index(request):
    """웹 인터페이스 메인 페이지"""
    return render(request, 'sanitization/index.html')
