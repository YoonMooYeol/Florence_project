from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as filters
from .models import Event
from .serializers import EventSerializer, EventDetailSerializer
from datetime import datetime
from calendar import monthrange
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import EventConversationSummary
from .serializers import (
    EventConversationSummarySerializer, 
    EventConversationSummaryDetailSerializer,
    MonthlyConversationSummarySerializer,
    DailyConversationSummarySerializer
)
from llm.models import LLMConversation
import logging

logger = logging.getLogger(__name__)

class EventFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name='event_day', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='event_day', lookup_expr='lte')
    
    class Meta:
        model = Event
        fields = ['event_day', 'event_type', 'pregnancy', 'start_date', 'end_date']

class EventViewSet(viewsets.ModelViewSet):
    """
    일정 관리 ViewSet
    
    list: 일정 목록 조회 (월별/일별 필터링 가능)
    retrieve: 일정 상세 조회
    create: 일정 생성
    update: 일정 수정
    destroy: 일정 삭제
    """
    permission_classes = [IsAuthenticated]
    filterset_class = EventFilter
    
    def get_queryset(self):
        # 사용자의 임신 정보에 해당하는 일정만 조회
        return Event.objects.filter(
            pregnancy__user=self.request.user
        )
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'create', 'update', 'partial_update']:
            return EventDetailSerializer
        return EventSerializer

    def perform_create(self, serializer):
        serializer.save()

class MonthlyConversationSummaryView(APIView):
    """월별 LLM 대화 요약 조회 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """월별 LLM 대화 요약 조회"""
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        # 파라미터 검증
        try:
            year = int(year) if year else timezone.now().year
            month = int(month) if month else timezone.now().month
            if not (1 <= month <= 12):
                return Response({"error": "월은 1에서 12 사이의 값이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({"error": "유효한 연도와 월을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 사용자의 임신 정보를 가져옴
        pregnancy = request.user.pregnancies.filter(is_active=True).first()
        if not pregnancy:
            return Response({"error": "활성화된 임신 정보가 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        
        # 해당 월의 날짜 범위 계산
        _, last_day = monthrange(year, month)
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day}"
        
        # 해당 월에 속하는 이벤트 요약 조회
        summaries = EventConversationSummary.objects.filter(
            event__pregnancy=pregnancy,
            generated_date__range=[start_date, end_date]
        ).order_by('generated_date')
        
        # 응답 데이터 구성
        data = {
            'year': year,
            'month': month,
            'event_summaries': EventConversationSummarySerializer(summaries, many=True).data
        }
        
        return Response(data, status=status.HTTP_200_OK)

class DailyConversationSummaryView(APIView):
    """일별 LLM 대화 요약 조회 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """일별 LLM 대화 요약 조회"""
        date_str = request.query_params.get('date')
        
        # 파라미터 검증
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
        except ValueError:
            return Response({"error": "유효한 날짜 형식(YYYY-MM-DD)을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 사용자의 임신 정보를 가져옴
        pregnancy = request.user.pregnancies.filter(is_active=True).first()
        if not pregnancy:
            return Response({"error": "활성화된 임신 정보가 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        
        # 해당 날짜의 이벤트 요약 조회
        summaries = EventConversationSummary.objects.filter(
            event__pregnancy=pregnancy,
            generated_date=date
        ).order_by('event__event_time')
        
        # 응답 데이터 구성
        data = {
            'date': date,
            'event_summaries': EventConversationSummarySerializer(summaries, many=True).data
        }
        
        return Response(data, status=status.HTTP_200_OK)

class EventConversationSummaryDetailView(APIView):
    """일정별 LLM 대화 요약 상세 조회 API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, summary_id):
        """일정별 LLM 대화 요약 상세 조회"""
        # 사용자의 임신 정보를 가져옴
        pregnancy = request.user.pregnancies.filter(is_active=True).first()
        if not pregnancy:
            return Response({"error": "활성화된 임신 정보가 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        
        # 요약 정보 조회
        summary = get_object_or_404(
            EventConversationSummary, 
            summary_id=summary_id,
            event__pregnancy=pregnancy
        )
        
        # 연관된 대화 포함하여 응답
        serializer = EventConversationSummaryDetailSerializer(summary)
        data = serializer.data
        
        # 관련 대화 목록 추가
        data['conversations'] = [
            {
                'id': conv.id,
                'query': conv.query,
                'response': conv.response,
                'created_at': conv.created_at
            }
            for conv in summary.conversations.all().order_by('created_at')
        ]
        
        return Response(data, status=status.HTTP_200_OK)

class EventConversationSummaryCreateView(APIView):
    """LLM 대화 요약 생성 API"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """일정 대화 요약 생성"""
        event_id = request.data.get('event_id')
        date_str = request.data.get('date')
        
        # 파라미터 검증
        if not event_id:
            return Response({"error": "일정 ID를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else timezone.now().date()
        except ValueError:
            return Response({"error": "유효한 날짜 형식(YYYY-MM-DD)을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 사용자의 임신 정보 확인
        pregnancy = request.user.pregnancies.filter(is_active=True).first()
        if not pregnancy:
            return Response({"error": "활성화된 임신 정보가 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        
        # 이벤트 조회
        try:
            event = Event.objects.get(event_id=event_id, pregnancy=pregnancy)
        except Event.DoesNotExist:
            return Response({"error": "해당 일정을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        
        # 해당 일정에 대한 대화 조회 (당일 생성된 대화만)
        conversations = LLMConversation.objects.filter(
            user=request.user,
            created_at__date=date
        ).order_by('created_at')
        
        if not conversations.exists():
            return Response({"error": "해당 날짜에 생성된 대화가 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        
        # 대화 내용 수집 및 요약 생성
        conversation_text = ""
        for conv in conversations:
            conversation_text += f"사용자: {conv.query}\n"
            conversation_text += f"챗봇: {conv.response}\n\n"
        
        # LLM을 사용한 요약 생성 로직 (필요 시 추가)
        # ChatGPT API 등을 이용해 요약 생성하는 코드 작성
        # 여기서는 예시로 간단하게 처리
        summary_text = f"{date}의 {event.title}에 관한 대화 요약"
        
        # 기존 요약이 있으면 업데이트, 없으면 새로 생성
        summary, created = EventConversationSummary.objects.update_or_create(
            event=event,
            generated_date=date,
            defaults={
                'summary_text': summary_text
            }
        )
        
        # 관련 대화 연결
        summary.conversations.set(conversations)
        
        serializer = EventConversationSummaryDetailSerializer(summary)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class EventConversationSummaryDeleteView(APIView):
    """LLM 대화 요약 삭제 API"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, summary_id):
        """일정 대화 요약 삭제"""
        # 사용자의 임신 정보 확인
        pregnancy = request.user.pregnancies.filter(is_active=True).first()
        if not pregnancy:
            return Response({"error": "활성화된 임신 정보가 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        
        # 요약 조회
        try:
            summary = EventConversationSummary.objects.get(
                summary_id=summary_id,
                event__pregnancy=pregnancy
            )
        except EventConversationSummary.DoesNotExist:
            return Response({"error": "해당 요약을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        
        # 요약 삭제
        summary.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)