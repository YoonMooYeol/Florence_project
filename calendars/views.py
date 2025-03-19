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
from datetime import datetime, timedelta
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
    retrieve: 특정 날짜의 아기 일기 상세 조회
    create: 아기 일기 생성 (하루에 하나씩만 생성 가능)
    update: 아기 일기 수정
    destroy: 아기 일기 삭제
    """
    permission_classes = [IsAuthenticated]  # 로그인한 사용자만 접근
    lookup_field = 'pregnancy_id'  # pregnancy_id로 조회

    def get_queryset(self):
        user = self.request.user
        return BabyDiary.objects.filter(user=user)

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

    def perform_update(self, serializer):
        """
        아기 일기 수정 시 해당 일기를 수정합니다.
        """
        user = self.request.user
        pregnancy_id = self.kwargs['pregnancy_id']
        pregnancy = get_object_or_404(Pregnancy, pregnancy_id=pregnancy_id, user=user)

        baby_diary = self.get_object()
        baby_diary.pregnancy = pregnancy  # pregnancy 업데이트
        serializer.save()

    def perform_destroy(self, instance):
        """
        아기 일기 삭제 시 해당 일기를 삭제합니다.
        """
        instance.delete()


class BabyDiaryPhotoView(APIView):
    """
    태교일기 사진 CRUD API
    """

    parser_classes = [MultiPartParser, FormParser]
    def post(self, request, diary_id):
        diary = get_object_or_404(BabyDiary, diary_id=diary_id, user=request.user)

        # 여러 이미지를 처리
        photo = request.FILES.getlist('image')  # 'image'는 Postman에서 form-data로 보낸 key 값

        # BabyDiaryPhoto 객체들을 하나씩 생성하여 저장
        saved_photos = []
        for photo in photo:
            photo_instance = BabyDiaryPhoto.objects.create(
                babydiary=diary,
                image=photo
            )
            saved_photos.append(photo_instance)

        # 저장된 사진들을 직렬화하여 응답 반환
        serializer = BabyDiaryPhotoSerializer(saved_photos, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, diary_id):
        """
        태교일기 사진 조회
        """
        diary_photos = BabyDiaryPhoto.objects.filter(babydiary__diary_id=diary_id, babydiary__user=request.user)
        serializer = BabyDiaryPhotoSerializer(diary_photos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


    def patch(self, request, diary_id, pk):
        """
        태교일기 사진 부분 수정 (이미지 수정 등)
        """
        diary = get_object_or_404(BabyDiary, diary_id=diary_id, user=request.user)
        photo = get_object_or_404(BabyDiaryPhoto, pk=pk, babydiary=diary)

        serializer = BabyDiaryPhotoSerializer(photo, data=request.data, partial=True)
        if serializer.is_valid():
            if "image" in request.data:
                # 기존 이미지 삭제 후 새 이미지 저장
                photo.image.delete(save=False)
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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