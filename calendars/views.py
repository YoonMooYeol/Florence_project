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