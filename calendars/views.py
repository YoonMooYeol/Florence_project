from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters import rest_framework as filters
from .models import Event, DailyConversationSummary, BabyDiary, Pregnancy
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
from datetime import datetime, timedelta, date
import os
from openai import OpenAI
from dotenv import load_dotenv
from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import BabyDiary, BabyDiaryPhoto
from .serializers import BabyDiaryPhotoSerializer
from django.db.models import Q
import json
import copy
import calendar

# .env 파일에서 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

class EventFilter(filters.FilterSet):
    start_date_from = filters.DateFilter(field_name='start_date', lookup_expr='gte')
    start_date_to = filters.DateFilter(field_name='start_date', lookup_expr='lte')
    end_date_from = filters.DateFilter(field_name='end_date', lookup_expr='gte')
    end_date_to = filters.DateFilter(field_name='end_date', lookup_expr='lte')
    
    class Meta:
        model = Event
        fields = ['start_date', 'end_date', 'event_type', 'start_date_from', 'start_date_to', 'end_date_from', 'end_date_to']

class EventViewSet(viewsets.ViewSet):
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
    
    def list(self, request):
        """
        기본 쿼리셋을 가져오고, 반복 일정에 대해 가상 인스턴스를 생성합니다.
        """
        # 쿼리 파라미터 로깅
        start_date_from = request.query_params.get('start_date_from')
        start_date_to = request.query_params.get('start_date_to')
        
        logger.info(f"Filtering events with start_date_from: {start_date_from}, start_date_to: {start_date_to}")
        
        # 사용자의 일정만 조회
        queryset = Event.objects.filter(user=request.user)
        
        # 날짜 범위 필터링
        if start_date_from:
            queryset = queryset.filter(
                Q(start_date__gte=start_date_from) | 
                Q(recurrence_rules__isnull=False)  # 반복 일정은 별도 처리
            )
        if start_date_to:
            # 날짜 범위 내에 있는 이벤트를 모두 포함
            # 1. start_date가 범위 내인 경우
            # 2. end_date가 범위 내인 경우
            # 3. 이벤트가 날짜 범위를 완전히 포함하는 경우
            date_range_query = Q(start_date__lte=start_date_to) & (
                Q(end_date__isnull=True) | Q(end_date__gte=start_date_from)
            )
            non_recurring_queryset = queryset.filter(
                Q(recurrence_rules__isnull=True) & date_range_query
            )
        else:
            non_recurring_queryset = queryset.filter(recurrence_rules__isnull=True)

        # 반복 일정 처리
        recurring_queryset = queryset.filter(recurrence_rules__isnull=False)
        
        # 결과 리스트 준비
        result_events = list(non_recurring_queryset)
        
        # 날짜 범위가 지정된 경우에만 반복 이벤트 확장
        if start_date_from and start_date_to:
            start_date_from_obj = datetime.strptime(start_date_from, '%Y-%m-%d').date()
            start_date_to_obj = datetime.strptime(start_date_to, '%Y-%m-%d').date()
            
            # 각 반복 일정에 대해 가상 인스턴스 생성
            for event in recurring_queryset:
                virtual_instances = self._expand_recurring_event(
                    event, start_date_from_obj, start_date_to_obj
                )
                result_events.extend(virtual_instances)
        
        logger.info(f"Total events (including virtual recurring instances): {len(result_events)}")
        
        serializer = EventSerializer(result_events, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        event = get_object_or_404(Event, event_id=pk, user=request.user)
        serializer = EventDetailSerializer(event)
        return Response(serializer.data)
    
    def create(self, request):
        serializer = EventDetailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, pk=None):
        event = get_object_or_404(Event, event_id=pk, user=request.user)
        serializer = EventDetailSerializer(event, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def partial_update(self, request, pk=None):
        event = get_object_or_404(Event, event_id=pk, user=request.user)
        serializer = EventDetailSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def destroy(self, request, pk=None):
        """
        일정 삭제 메서드 (단일 일정 삭제)
        """
        event = get_object_or_404(Event, event_id=pk, user=request.user)
        event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['delete'])
    def delete_recurring(self, request, pk=None):
        """
        반복 일정 삭제를 위한 추가 API 엔드포인트
        
        query parameters:
        - delete_type: 삭제 유형 (this_only, this_and_future, all)
        - event_date: 타겟 날짜 (가상 인스턴스의 경우 필요, YYYY-MM-DD 형식)
        """
        event = get_object_or_404(Event, event_id=pk, user=request.user)
        delete_type = request.query_params.get('delete_type', 'this_only')
        event_date_str = request.query_params.get('event_date')
        
        # 날짜 파싱
        if event_date_str:
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "event_date는 YYYY-MM-DD 형식이어야 합니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            event_date = event.start_date
        
        if not event.recurrence_rules:
            # 반복 일정이 아닌 경우 그냥 삭제
            event.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        # 1. 이 일정만 삭제 (예외 추가)
        if delete_type == 'this_only':
            recurrence_rules = event.recurrence_rules.copy()
            exceptions = recurrence_rules.get('exceptions', [])
            exceptions.append(event_date.strftime('%Y-%m-%d'))
            recurrence_rules['exceptions'] = exceptions
            
            # 원본 일정의 recurrence_rules 업데이트
            event.recurrence_rules = recurrence_rules
            event.save()
            
        # 2. 이 일정과 이후의 모든 반복 일정 삭제 (until 설정)
        elif delete_type == 'this_and_future':
            # 타겟 날짜가 원본 시작일과 같거나 이전이면 완전 삭제
            if event_date <= event.start_date:
                event.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            
            # 아니면 until 설정 (하루 전까지만 반복)
            recurrence_rules = event.recurrence_rules.copy()
            until_date = (event_date - timedelta(days=1)).strftime('%Y-%m-%d')
            recurrence_rules['until'] = until_date
            event.recurrence_rules = recurrence_rules
            event.save()
        
        # 3. 모든 반복 일정 삭제 (원본 삭제)
        elif delete_type == 'all':
            event.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['put', 'patch'])
    def update_recurring(self, request, pk=None):
        """
        반복 일정 수정을 위한 추가 API 엔드포인트
        
        query parameters:
        - update_type: 수정 유형 (this_only, this_and_future, all)
        - event_date: 타겟 날짜 (가상 인스턴스의 경우 필요, YYYY-MM-DD 형식)
        """
        event = get_object_or_404(Event, event_id=pk, user=request.user)
        update_type = request.query_params.get('update_type', 'this_only')
        event_date_str = request.query_params.get('event_date')
        
        # 날짜 파싱
        if event_date_str:
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "event_date는 YYYY-MM-DD 형식이어야 합니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            event_date = event.start_date
        
        if not event.recurrence_rules:
            # 반복 일정이 아닌 경우 일반 업데이트
            serializer = EventDetailSerializer(event, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        
        # 1. 이 일정만 수정 (예외 추가 + 새 일정 생성)
        if update_type == 'this_only':
            # 예외 날짜 추가
            recurrence_rules = event.recurrence_rules.copy()
            exceptions = recurrence_rules.get('exceptions', [])
            exceptions.append(event_date.strftime('%Y-%m-%d'))
            recurrence_rules['exceptions'] = exceptions
            event.recurrence_rules = recurrence_rules
            event.save()
            
            # 새 단일 일정 생성
            new_data = request.data.copy()
            new_data['start_date'] = event_date_str  # 수정 대상 날짜로 설정
            new_data['recurrence_rules'] = None      # 반복 규칙 없음 (단일 일정)
            
            # 이벤트 기간 계산 (멀티데이 이벤트인 경우)
            if event.end_date:
                duration = (event.end_date - event.start_date).days
                new_end_date = event_date + timedelta(days=duration)
                new_data['end_date'] = new_end_date.strftime('%Y-%m-%d')
            
            serializer = EventDetailSerializer(data=new_data)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=self.request.user)
            
            return Response(serializer.data)
        
        # 2. 이 일정과 이후의 모든 반복 일정 수정
        elif update_type == 'this_and_future':
            # 기존 반복 일정 종료
            recurrence_rules = event.recurrence_rules.copy()
            until_date = (event_date - timedelta(days=1)).strftime('%Y-%m-%d')
            recurrence_rules['until'] = until_date
            event.recurrence_rules = recurrence_rules
            event.save()
            
            # 새 반복 일정 생성
            new_data = request.data.copy()
            new_data['start_date'] = event_date_str  # 수정 대상 날짜로 설정
            
            # # recurrence_rules이 요청에 없으면 원본 일정의 recurrence_rules 복사. 프론트엔드에서 대신 처리해줌
            # if 'recurrence_rules' not in new_data:
            #     new_data['recurrence_rules'] = event.recurrence_rules

            # 이벤트 기간 계산 (멀티데이 이벤트인 경우)
            if event.end_date:
                duration = (event.end_date - event.start_date).days
                new_end_date = event_date + timedelta(days=duration)
                new_data['end_date'] = new_end_date.strftime('%Y-%m-%d')
            
            serializer = EventDetailSerializer(data=new_data)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=self.request.user)
            
            return Response(serializer.data)
        
        # 3. 모든 반복 일정 수정
        elif update_type == 'all':
            # 원본 일정 업데이트
            serializer = EventDetailSerializer(event, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
                
            return Response(serializer.data)
                
        return Response({"error": "잘못된 update_type 값입니다."}, status=status.HTTP_400_BAD_REQUEST)

    def _expand_recurring_event(self, event, start_date, end_date):
        """
        반복 일정에 대해 지정된 날짜 범위 내의 가상 인스턴스 생성
        """
        if not event.recurrence_rules:
            return []
        
        recurrence_rules = event.recurrence_rules
        pattern = recurrence_rules.get('pattern')
        until_date_str = recurrence_rules.get('until')
        exceptions = recurrence_rules.get('exceptions', [])
        
        # 종료일이 지정되어 있지 않은 경우 기본값 설정 (1년)
        if until_date_str:
            until_date = datetime.strptime(until_date_str, '%Y-%m-%d').date()
        else:
            until_date = event.start_date + timedelta(days=365)
        
        # 조회 범위의 종료일이 반복 종료일보다 이후인 경우 종료일로 제한
        end_date = min(end_date, until_date)
        
        # 조회 범위가 반복 시작일보다 이전이거나, 반복 종료일보다 이후인 경우 빈 리스트 반환
        if end_date < event.start_date or start_date > until_date:
            return []
        
        # 멀티데이 이벤트인 경우 일정 기간 계산
        event_duration = None
        if event.end_date:
            event_duration = (event.end_date - event.start_date).days
        
        # 결과 리스트 준비
        virtual_instances = []
        
        # 첫 날짜가 조회 범위 내에 있으면 원본 이벤트 추가
        if start_date <= event.start_date <= end_date:
            if event.start_date.strftime('%Y-%m-%d') not in exceptions:
                virtual_instances.append(event)
        
        # 패턴별 처리
        if pattern == 'daily':
            # 매일 반복
            current_date = event.start_date + timedelta(days=1)  # 원본 다음날부터 시작
            
            while current_date <= end_date:
                if current_date < start_date:
                    current_date += timedelta(days=1)
                    continue
                    
                # 예외 날짜 확인
                if current_date.strftime('%Y-%m-%d') in exceptions:
                    current_date += timedelta(days=1)
                    continue
                
                # 가상 인스턴스 생성
                instance = self._create_virtual_instance(
                    event, current_date, event_duration
                )
                virtual_instances.append(instance)
                
                current_date += timedelta(days=1)
                
        elif pattern == 'weekly':
            # 매주 반복 (같은 요일)
            current_date = event.start_date + timedelta(days=7)  # 1주일 후부터 시작
            
            while current_date <= end_date:
                if current_date < start_date:
                    current_date += timedelta(days=7)
                    continue
                    
                # 예외 날짜 확인
                if current_date.strftime('%Y-%m-%d') in exceptions:
                    current_date += timedelta(days=7)
                    continue
                
                # 가상 인스턴스 생성
                instance = self._create_virtual_instance(
                    event, current_date, event_duration
                )
                virtual_instances.append(instance)
                
                current_date += timedelta(days=7)
                
        elif pattern == 'monthly':
            # 매월 반복 (같은 날짜)
            day_of_month = event.start_date.day
            
            # 첫 번째 반복일 계산 (다음 달 같은 날짜)
            if event.start_date.month == 12:
                next_month = 1
                next_year = event.start_date.year + 1
            else:
                next_month = event.start_date.month + 1
                next_year = event.start_date.year
            
            last_day = calendar.monthrange(next_year, next_month)[1]
            actual_day = min(day_of_month, last_day)
            
            try:
                current_date = date(next_year, next_month, actual_day)
            except ValueError:
                # 유효하지 않은 날짜인 경우 다음 달 1일
                current_date = date(next_year, next_month, 1)
            
            # 매월 반복 계산
            while current_date <= end_date:
                if current_date < start_date:
                    # 다음 달로 이동
                    if current_date.month == 12:
                        next_month = 1
                        next_year = current_date.year + 1
                    else:
                        next_month = current_date.month + 1
                        next_year = current_date.year
                    
                    last_day = calendar.monthrange(next_year, next_month)[1]
                    actual_day = min(day_of_month, last_day)
                    
                    try:
                        current_date = date(next_year, next_month, actual_day)
                    except ValueError:
                        current_date = date(next_year, next_month, 1)
                    continue
                
                # 예외 날짜 확인
                if current_date.strftime('%Y-%m-%d') in exceptions:
                    # 다음 달로 이동
                    if current_date.month == 12:
                        next_month = 1
                        next_year = current_date.year + 1
                    else:
                        next_month = current_date.month + 1
                        next_year = current_date.year
                    
                    last_day = calendar.monthrange(next_year, next_month)[1]
                    actual_day = min(day_of_month, last_day)
                    
                    try:
                        current_date = date(next_year, next_month, actual_day)
                    except ValueError:
                        current_date = date(next_year, next_month, 1)
                    continue
                
                # 가상 인스턴스 생성
                instance = self._create_virtual_instance(
                    event, current_date, event_duration
                )
                virtual_instances.append(instance)
                
                # 다음 달로 이동
                if current_date.month == 12:
                    next_month = 1
                    next_year = current_date.year + 1
                else:
                    next_month = current_date.month + 1
                    next_year = current_date.year
                
                last_day = calendar.monthrange(next_year, next_month)[1]
                actual_day = min(day_of_month, last_day)
                
                try:
                    current_date = date(next_year, next_month, actual_day)
                except ValueError:
                    current_date = date(next_year, next_month, 1)
                
        elif pattern == 'yearly':
            # 매년 반복 (같은 월, 같은 날)
            origin_month = event.start_date.month
            origin_day = event.start_date.day
            
            # 다음 해부터 시작
            for year in range(event.start_date.year + 1, end_date.year + 1):
                try:
                    current_date = date(year, origin_month, origin_day)
                    
                    if current_date > end_date:
                        break
                        
                    if current_date < start_date:
                        continue
                    
                    # 예외 날짜 확인
                    if current_date.strftime('%Y-%m-%d') in exceptions:
                        continue
                    
                    # 가상 인스턴스 생성
                    instance = self._create_virtual_instance(
                        event, current_date, event_duration
                    )
                    virtual_instances.append(instance)
                    
                except ValueError:
                    # 윤년 관련 문제 (2월 29일 등) - 건너뜀
                    continue
        
        return virtual_instances

    def _create_virtual_instance(self, event, new_date, duration=None):
        """
        반복 일정의 가상 인스턴스를 생성합니다.
        """
        # 이벤트 객체 복사 (얕은 복사)
        instance = copy.copy(event)
        
        # 가상 인스턴스임을 표시하는 속성 추가
        instance._is_virtual = True
        instance._original_event_id = event.event_id
        
        # 날짜 설정
        instance.start_date = new_date
        if duration is not None:
            instance.end_date = new_date + timedelta(days=duration)
        else:
            instance.end_date = None
        
        return instance

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
    retrieve: 특정 날짜의 아기 일기 상세 조회
    create: 아기 일기 생성 (하루에 하나씩만 생성 가능)
    update: 아기 일기 수정
    destroy: 아기 일기 삭제
    
    retrieve_by_id: diary_id로 아기 일기 상세 조회
    update_by_id: diary_id로 아기 일기 수정
    partial_update_by_id: diary_id로 아기 일기 부분 수정
    destroy_by_id: diary_id로 아기 일기 삭제
    """
    permission_classes = [IsAuthenticated]  # 로그인한 사용자만 접근
    lookup_field = 'pregnancy_id'  # pregnancy_id로 조회

    def get_queryset(self):
        user = self.request.user
        return BabyDiary.objects.filter(user=user)
        
    def get_baby_diary_by_id(self, diary_id):
        """
        diary_id로 아기 일기를 조회합니다.
        """
        obj = get_object_or_404(BabyDiary, diary_id=diary_id, user=self.request.user)
        self.check_object_permissions(self.request, obj)
        return obj

    def get_object(self):
        pregnancy_id = self.kwargs['pregnancy_id']
        diary_date = self.kwargs['diary_date']

        # pregnancy_id와 diary_date로 여러 개의 BabyDiary가 존재할 수 있기 때문에 첫 번째 결과만 반환
        obj = self.get_queryset().filter(pregnancy_id=pregnancy_id, diary_date=diary_date).first()

        if obj is None:
            raise NotFound("해당 아기 일기가 존재하지 않습니다.")

        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_class(self):
        """
        생성과 조회/수정에 대해 다른 Serializer를 사용
        """
        if self.action == 'create':
            return BabyDiaryCreateSerializer
        return BabyDiarySerializer
        
    # diary_id로 아기 일기 조회
    def retrieve_by_id(self, request, diary_id=None):
        """
        diary_id로 아기 일기를 조회합니다.
        """
        diary = self.get_baby_diary_by_id(diary_id)
        serializer = BabyDiarySerializer(diary)
        return Response(serializer.data)
        
    # diary_id로 아기 일기 수정
    def update_by_id(self, request, diary_id=None):
        """
        diary_id로 아기 일기를 수정합니다.
        """
        diary = self.get_baby_diary_by_id(diary_id)
        serializer = BabyDiarySerializer(diary, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    # diary_id로 아기 일기 부분 수정
    def partial_update_by_id(self, request, diary_id=None):
        """
        diary_id로 아기 일기를 부분 수정합니다.
        """
        diary = self.get_baby_diary_by_id(diary_id)
        serializer = BabyDiarySerializer(diary, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    # diary_id로 아기 일기 삭제
    def destroy_by_id(self, request, diary_id=None):
        """
        diary_id로 아기 일기를 삭제합니다.
        """
        diary = self.get_baby_diary_by_id(diary_id)
        diary.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_create(self, serializer):
        """
        아기 일기 생성 시 pregnancy_id를 기준으로 Pregnancy 객체를 가져와
        연결하고, 생성된 태교일기를 반환합니다.
        """
        user = self.request.user
        pregnancy_id = self.kwargs['pregnancy_id']
        pregnancy = get_object_or_404(Pregnancy, pregnancy_id=pregnancy_id, user=user)

        diary_date = serializer.validated_data['diary_date']
        content = serializer.validated_data.get('content', '')

        # 같은 diary_date가 존재하면 업데이트, 없으면 생성
        baby_diary, created = BabyDiary.objects.update_or_create(
            user=user,
            diary_date=diary_date,  # 중복 체크할 필드
            defaults={'content': content, 'pregnancy': pregnancy}
        )

        # diary_id를 serializer에 설정하여 응답에 포함되도록 함
        if hasattr(serializer, 'instance'):
            serializer.instance = baby_diary

        return baby_diary


class BabyDiaryPhotoView(APIView):
    """
    태교일기 사진 CRUD API
    """

    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, diary_id):
        try:
            # 디버깅 로그 추가
            print(f"\n\n===== BabyDiaryPhotoView.post 시작: diary_id={diary_id} =====")
            print(f"Request method: {request.method}")
            print(f"Request user: {request.user}")
            print(f"Request FILES keys: {list(request.FILES.keys())}")
            print(f"Request FILES keys (all): {request.FILES.keys()}")
            print(f"Request POST keys: {list(request.POST.keys())}")
            
            # 'image' 필드 존재 여부 및 값 확인
            has_image_field = 'image' in request.FILES
            image_files_count = len(request.FILES.getlist('image')) if has_image_field else 0
            print(f"'image' 필드 존재 여부: {has_image_field}")
            print(f"'image' 필드 파일 개수: {image_files_count}")
            
            if has_image_field:
                for i, file in enumerate(request.FILES.getlist('image')):
                    print(f"파일 {i+1} 정보: 이름={file.name}, 크기={file.size}, 타입={file.content_type}")
            
            # 필수 헤더 확인
            auth_header = request.headers.get('Authorization', None)
            content_type = request.headers.get('Content-Type', None)
            print(f"Authorization 헤더: {auth_header[:20]}... (일부만 표시)" if auth_header else "Authorization 헤더 없음")
            print(f"Content-Type 헤더: {content_type}")
            
            diary = get_object_or_404(BabyDiary, diary_id=diary_id, user=request.user)
            
            # 로그 추가: 업로드 시작
            print(f"BabyDiaryPhotoView.post: 사진 업로드 시작 - diary_id: {diary_id}")
            
            # request.FILES가 있는지 확인
            if not request.FILES:
                print("BabyDiaryPhotoView.post: Error - request.FILES가 비어있습니다.")
                return Response({"error": "업로드된 파일이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

            # 여러 이미지를 처리
            photos = request.FILES.getlist('image')  # 'image'는 Postman에서 form-data로 보낸 key 값
            
            # 파일 목록 확인
            if not photos:
                print("BabyDiaryPhotoView.post: Error - 'image' 필드에 파일이 없습니다.")
                # 다른 가능한 필드 이름 체크
                all_file_fields = list(request.FILES.keys())
                if all_file_fields:
                    print(f"사용 가능한 파일 필드: {all_file_fields}")
                    # 첫 번째 필드 사용 시도
                    alt_field = all_file_fields[0]
                    photos = request.FILES.getlist(alt_field)
                    print(f"대체 필드 '{alt_field}'에서 {len(photos)}개 파일 찾음")
                else:
                    return Response({"error": "'image' 필드에 파일이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
                
            print(f"BabyDiaryPhotoView.post: 업로드할 사진 개수: {len(photos)}")
            
            # 업로드 디렉토리가 있는지 확인하고 없으면 생성
            from django.conf import settings
            
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'baby_diary_photos', 
                                    datetime.now().strftime('%Y/%m/%d'))
            
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)
                print(f"BabyDiaryPhotoView.post: 업로드 디렉토리 생성: {upload_dir}")

            # BabyDiaryPhoto 객체들을 하나씩 생성하여 저장
            saved_photos = []
            for i, photo in enumerate(photos):
                try:
                    print(f"BabyDiaryPhotoView.post: 사진 {i+1}/{len(photos)} 저장 시작 - 파일명: {photo.name}")
                    
                    photo_instance = BabyDiaryPhoto.objects.create(
                        babydiary=diary,
                        image=photo
                    )
                    saved_photos.append(photo_instance)
                    print(f"BabyDiaryPhotoView.post: 사진 {i+1}/{len(photos)} 저장 성공 - photo_id: {photo_instance.photo_id}")
                except Exception as photo_error:
                    print(f"BabyDiaryPhotoView.post: 사진 {i+1}/{len(photos)} 저장 실패: {photo_error}")
                    # 저장 도중 오류가 발생하면 다음 사진으로 넘어감

            # 저장된 사진이 없는 경우
            if not saved_photos:
                print("BabyDiaryPhotoView.post: Error - 모든 사진 저장에 실패했습니다.")
                return Response({"error": "사진 저장에 실패했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 저장된 사진들을 직렬화하여 응답 반환
            serializer = BabyDiaryPhotoSerializer(saved_photos, many=True)
            
            # 응답 데이터에 썸네일 URL 추가
            response_data = serializer.data
            for i, photo_instance in enumerate(saved_photos):
                try:
                    thumbnail_url = photo_instance.thumbnail_url
                    if thumbnail_url:
                        response_data[i]['image_thumbnail'] = thumbnail_url
                        print(f"BabyDiaryPhotoView.post: 사진 {i+1}/{len(saved_photos)} 썸네일 생성 성공")
                    else:
                        print(f"BabyDiaryPhotoView.post: 사진 {i+1}/{len(saved_photos)} 썸네일 생성 실패 - 썸네일 URL이 None임")
                        response_data[i]['image_thumbnail'] = response_data[i]['image']
                except Exception as e:
                    print(f"BabyDiaryPhotoView.post: 사진 {i+1}/{len(saved_photos)} 썸네일 URL 생성 중 오류 발생: {e}")
                    response_data[i]['image_thumbnail'] = response_data[i]['image']
            
            print(f"BabyDiaryPhotoView.post: 사진 업로드 완료 - 저장된 사진 개수: {len(saved_photos)}")
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            print(f"BabyDiaryPhotoView.post: 예상치 못한 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, diary_id):
        """
        태교일기 사진 조회
        """
        try:
            diary_photos = BabyDiaryPhoto.objects.filter(babydiary__diary_id=diary_id, babydiary__user=request.user)
            serializer = BabyDiaryPhotoSerializer(diary_photos, many=True)
            
            # 응답 데이터에 썸네일 URL 추가
            response_data = serializer.data
            for i, photo_instance in enumerate(diary_photos):
                try:
                    response_data[i]['image_thumbnail'] = photo_instance.thumbnail_url
                except Exception as e:
                    print(f"썸네일 URL 생성 중 오류 발생: {e}")
                    response_data[i]['image_thumbnail'] = response_data[i]['image']
            
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, diary_id, pk):
        """
        태교일기 사진 부분 수정 (이미지 수정 등)
        """
        try:
            diary = get_object_or_404(BabyDiary, diary_id=diary_id, user=request.user)
            photo = get_object_or_404(BabyDiaryPhoto, pk=pk, babydiary=diary)

            serializer = BabyDiaryPhotoSerializer(photo, data=request.data, partial=True)
            if serializer.is_valid():
                if "image" in request.data:
                    try:
                        # 기존 이미지 삭제 후 새 이미지 저장
                        photo.image.delete(save=False)
                    except Exception as e:
                        print(f"기존 이미지 삭제 중 오류 발생: {e}")
                        # 오류가 발생해도 계속 진행 (새 이미지는 저장)
                photo_instance = serializer.save()
                
                # 응답에 썸네일 URL 추가
                response_data = serializer.data
                try:
                    response_data['image_thumbnail'] = photo_instance.thumbnail_url
                except Exception as e:
                    print(f"썸네일 URL 생성 중 오류 발생: {e}")
                    response_data['image_thumbnail'] = response_data['image']
                
                return Response(response_data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def put(self, request, diary_id, pk):
        """
        태교일기 사진 전체 수정 (이미지 교체)
        """
        try:
            diary = get_object_or_404(BabyDiary, diary_id=diary_id, user=request.user)
            photo = get_object_or_404(BabyDiaryPhoto, pk=pk, babydiary=diary)
            
            serializer = BabyDiaryPhotoSerializer(photo, data=request.data)
            if serializer.is_valid():
                if "image" in request.data:
                    try:
                        # 기존 이미지 삭제 후 새 이미지 저장
                        photo.image.delete(save=False)
                    except Exception as e:
                        print(f"기존 이미지 삭제 중 오류 발생: {e}")
                        # 오류가 발생해도 계속 진행 (새 이미지는 저장)
                photo_instance = serializer.save()
                
                # 응답에 썸네일 URL 추가
                response_data = serializer.data
                try:
                    response_data['image_thumbnail'] = photo_instance.thumbnail_url
                except Exception as e:
                    print(f"썸네일 URL 생성 중 오류 발생: {e}")
                    response_data['image_thumbnail'] = response_data['image']
                
                return Response(response_data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, diary_id, pk):
        """
        태교일기 사진 삭제
        """
        diary = get_object_or_404(BabyDiary, diary_id=diary_id, user=request.user)
        photo = get_object_or_404(BabyDiaryPhoto, pk=pk, babydiary=diary)

        # 사진 삭제 (파일 시스템에서 삭제)
        photo.image.delete(save=False)
        photo.delete()

        return Response({"detail": "사진이 삭제되었습니다."}, status=status.HTTP_204_NO_CONTENT)