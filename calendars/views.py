from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters import rest_framework as filters
from .models import Event, DailyConversationSummary, BabyDiary
from .serializers import (
    EventSerializer, 
    EventDetailSerializer,
    DailyConversationSummarySerializer,
    DailyConversationSummaryCreateSerializer,
    BabyDiarySerializer,
    BabyDiaryCreateSerializer
)
from llm.models import LLMConversation
import logging
from datetime import datetime, timedelta
import os
from openai import OpenAI
from dotenv import load_dotenv
from django.http import Http404
from django.utils import timezone

# .env 파일에서 환경 변수 로드
load_dotenv()

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
        # 쿼리 파라미터 로깅
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        event_day = self.request.query_params.get('event_day')
        
        logger.info(f"Filtering events with start_date: {start_date}, end_date: {end_date}, event_day: {event_day}")
        
        # 사용자의 임신 정보에 해당하는 일정만 조회
        queryset = Event.objects.filter(
            pregnancy__user=self.request.user
        )
        
        # 특정 날짜 필터링 (일별 조회)
        if event_day:
            queryset = queryset.filter(event_day=event_day)
            logger.info(f"Filtering by exact event_day: {event_day}")
        # 날짜 범위 필터링 (월별 조회)
        else:
            # 명시적으로 날짜 필터링 추가
            if start_date:
                queryset = queryset.filter(event_day__gte=start_date)
            if end_date:
                queryset = queryset.filter(event_day__lte=end_date)
        
        logger.info(f"Filtered event queryset count: {queryset.count()}")
        return queryset
    
    def get_serializer_class(self):
        if self.action in ['retrieve', 'create', 'update', 'partial_update']:
            return EventDetailSerializer
        return EventSerializer

    def perform_create(self, serializer):
        serializer.save()


class DailyConversationSummaryFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name='summary_date', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='summary_date', lookup_expr='lte')
    
    class Meta:
        model = DailyConversationSummary
        fields = ['summary_date', 'user', 'pregnancy', 'start_date', 'end_date']


class DailyConversationSummaryViewSet(viewsets.ModelViewSet):
    """
    일별 LLM 대화 요약 관리 ViewSet
    
    list: 대화 요약 목록 조회 (월별/일별 필터링 가능)
      - ?start_date=2023-01-01&end_date=2023-01-31 형식으로 월별 조회 가능
    retrieve: 대화 요약 상세 조회
    create: 대화 요약 생성 (하루에 하나씩만 생성 가능)
    update: 대화 요약 수정
    destroy: 대화 요약 삭제
    
    auto_summarize: 특정 날짜의 모든 대화를 자동으로 요약
      - POST /api/v1/calendars/conversation-summaries/auto_summarize/
      - body: {"summary_date": "2023-06-15"}
    """
    permission_classes = [IsAuthenticated]
    filterset_class = DailyConversationSummaryFilter
    
    def get_queryset(self):
        # 쿼리 파라미터 로깅
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        summary_date = self.request.query_params.get('summary_date')
        
        logger.info(f"Filtering summaries with start_date: {start_date}, end_date: {end_date}, summary_date: {summary_date}")
        
        # 사용자 본인의 대화 요약만 조회
        queryset = DailyConversationSummary.objects.filter(
            user=self.request.user
        )
        
        # 특정 날짜 필터링 (일별 조회)
        if summary_date:
            queryset = queryset.filter(summary_date=summary_date)
            logger.info(f"Filtering by exact date: {summary_date}")
        # 날짜 범위 필터링 (월별 조회)
        else:
            # 명시적으로 날짜 필터링 추가
            if start_date:
                queryset = queryset.filter(summary_date__gte=start_date)
            if end_date:
                queryset = queryset.filter(summary_date__lte=end_date)
        
        logger.info(f"Filtered queryset count: {queryset.count()}")
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DailyConversationSummaryCreateSerializer
        return DailyConversationSummarySerializer
    
    def perform_create(self, serializer):
        # 사용자 자동 설정
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def auto_summarize(self, request):
        """
        특정 날짜의 모든 대화를 자동으로 요약하는 API
        
        요청 예시:
        {
            "summary_date": "2023-06-15",  # 요약할 날짜 (기본값: 오늘)
            "pregnancy": "uuid"  # 선택적 임신 ID
        }
        """
        # 요청에서 날짜 파싱 (기본값: 오늘)
        summary_date_str = request.data.get('summary_date')
        pregnancy_id = request.data.get('pregnancy')
        
        try:
            if summary_date_str:
                summary_date = datetime.strptime(summary_date_str, '%Y-%m-%d').date()
            else:
                summary_date = datetime.now().date()
                
            # 이미 해당 날짜의 요약이 있는지 확인
            existing_summary = DailyConversationSummary.objects.filter(
                user=request.user,
                summary_date=summary_date
            ).first()
            
            if existing_summary:
                return Response(
                    {"error": f"이미 {summary_date} 날짜의 요약이 존재합니다. ID: {existing_summary.summary_id}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 해당 날짜의 대화 찾기
            start_naive = datetime.combine(summary_date, datetime.min.time())
            end_naive = datetime.combine(summary_date, datetime.max.time())
            
            # 시간대 정보 추가
            start_datetime = timezone.make_aware(start_naive)
            end_datetime = timezone.make_aware(end_naive)

            conversations = LLMConversation.objects.filter(
                user=request.user,
                created_at__gte=start_datetime,
                created_at__lte=end_datetime
            )
            
            if not conversations.exists():
                return Response(
                    {"error": f"{summary_date} 날짜에 해당하는 대화가 없습니다."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 대화 내용 수집
            conversation_texts = []
            conversation_ids = []
            
            for conversation in conversations:
                # conversation 자체가 하나의 질문-응답 쌍입니다
                conversation_text = f"대화 ID: {conversation.id}\n"
                conversation_text += f"사용자: {conversation.query}\n"
                conversation_text += f"AI: {conversation.response}\n"
                
                conversation_texts.append(conversation_text)
                conversation_ids.append(conversation.id)
            
            # LLM 호출하여 요약 생성
            all_conversations = "\n\n".join(conversation_texts)
            
            try:
                # OpenAI API 직접 호출 (GPT-4o mini 사용)
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    logger.error("OpenAI API 키가 설정되지 않았습니다.")
                    return Response(
                        {"error": "서비스 구성 오류가 발생했습니다. 관리자에게 문의하세요."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                client = OpenAI(api_key=api_key)
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # 더 가벼운 GPT-4o mini 모델 사용
                    messages=[
                        {"role": "system", "content": "당신은 임신 관련 정보를 요약해주는 전문가입니다. 캘린더에 기록될 '오늘의 하루' 요약을 생성해주세요. '대화에서', '대화에 따르면' 같은 표현을 사용하지 말고, 직접적으로 정보와 주제만 요약해주세요. 300자 이내로 작성하세요."},
                        {"role": "user", "content": "다음은 오늘 나눈 대화 내용입니다. 이 내용을 바탕으로 오늘의 주요 임신 관련 정보와 주제를 요약해주세요. 대화의 출처나 맥락을 언급하지 말고, 내용 자체만 요약해주세요:\n\n" + all_conversations}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                
                summary_text = response.choices[0].message.content.strip()
                
                # 요약 저장
                summary = DailyConversationSummary.objects.create(
                    user=request.user,
                    pregnancy_id=pregnancy_id,
                    summary_date=summary_date,
                    summary_text=summary_text
                )
                
                # 대화 연결
                summary.conversations.set(conversations)
                
                # 결과 반환
                serializer = DailyConversationSummarySerializer(summary)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"LLM 요약 생성 중 오류 발생: {str(e)}")
                return Response(
                    {"error": f"요약 생성 중 오류가 발생했습니다: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"자동 요약 중 오류 발생: {str(e)}")
            return Response(
                {"error": f"요약 생성 중 오류가 발생했습니다: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

class BabyDiaryFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name='diary_date', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='diary_date', lookup_expr='lte')
    
    class Meta:
        model = BabyDiary
        fields = ['diary_date', 'user', 'pregnancy', 'start_date', 'end_date']


class BabyDiaryViewSet(viewsets.ModelViewSet):
    """
    아기 일기 관리 ViewSet
    
    list: 아기 일기 목록 조회 (월별/일별 필터링 가능)
      - ?start_date=2023-01-01&end_date=2023-01-31 형식으로 월별 조회 가능
      - ?diary_date=2023-01-01 형식으로 특정 날짜 조회 가능
    retrieve: 특정 날짜의 아기 일기 상세 조회
    create: 아기 일기 생성 (하루에 하나씩만 생성 가능)
    update: 아기 일기 수정
    destroy: 아기 일기 삭제
    """
    permission_classes = [IsAuthenticated]
    filterset_class = BabyDiaryFilter
    lookup_field = 'diary_date'  # URL에서 날짜로 조회할 수 있도록 설정
    
    def get_queryset(self):
        # 쿼리 파라미터 로깅
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        diary_date = self.request.query_params.get('diary_date')
        
        logger.info(f"Filtering baby diaries with start_date: {start_date}, end_date: {end_date}, diary_date: {diary_date}")
        
        # 사용자 본인의 아기 일기만 조회
        queryset = BabyDiary.objects.filter(
            user=self.request.user
        )
        
        # 특정 날짜 필터링 (일별 조회)
        if diary_date:
            queryset = queryset.filter(diary_date=diary_date)
            logger.info(f"Filtering by exact diary_date: {diary_date}")
        # 날짜 범위 필터링 (월별 조회)
        else:
            # 명시적으로 날짜 필터링 추가
            if start_date:
                queryset = queryset.filter(diary_date__gte=start_date)
            if end_date:
                queryset = queryset.filter(diary_date__lte=end_date)
        
        logger.info(f"Filtered baby diary queryset count: {queryset.count()}")
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BabyDiaryCreateSerializer
        return BabyDiarySerializer
    
    def perform_create(self, serializer):
        # 사용자 자동 설정
        serializer.save(user=self.request.user)
        
    def get_object(self):
        """
        diary_date를 기준으로 객체를 조회하는 로직
        URL에서 날짜로 조회할 수 있도록 오버라이드
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # lookup_url_kwarg가 설정되지 않은 경우 기본값 사용
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        
        # URL에서 전달된 날짜 가져오기
        diary_date = self.kwargs[lookup_url_kwarg]
        
        try:
            # 사용자와 날짜로 객체 필터링
            obj = queryset.get(user=self.request.user, diary_date=diary_date)
            self.check_object_permissions(self.request, obj)
            return obj
        except BabyDiary.DoesNotExist:
            raise Http404("해당 날짜의 아기 일기가 존재하지 않습니다.")
