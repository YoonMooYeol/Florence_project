from django.db import models
import uuid
from accounts.models import User, Pregnancy
from sorl.thumbnail import get_thumbnail
import os



class MyImage(models.Model):
    image = models.ImageField(upload_to='images/')

    @property
    def thumbnail_url(self):
        return get_thumbnail(self.image, '200x200', crop='center', quality=90).url

class Event(models.Model):
    """일정 모델"""
    EVENT_TYPES = [
        ('appointment', '병원 예약'),
        ('medication', '약물 복용'),
        ('symptom', '증상 기록'),
        ('exercise', '운동'),
        ('other', '기타'),
    ]

    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pregnancy = models.ForeignKey(Pregnancy, on_delete=models.CASCADE, related_name='events', verbose_name='임신 정보')
    title = models.CharField(
        max_length=100, 
        verbose_name='제목',
        error_messages={
            'blank': '제목을 입력해주세요.',
            'max_length': '제목은 100자를 초과할 수 없습니다.'
        }
    )
    description = models.TextField(blank=True, null=True, verbose_name='설명')
    event_day = models.DateField(verbose_name='일정 날짜')
    event_time = models.TimeField(blank=True, null=True, verbose_name='일정 시간')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='other', verbose_name='일정 유형')
    is_recurring = models.BooleanField(default=False, verbose_name='반복 여부')
    recurrence_pattern = models.CharField(max_length=50, blank=True, null=True, verbose_name='반복 패턴')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['event_day', 'event_time']
        verbose_name = '일정'
        verbose_name_plural = '일정들'

    def __str__(self):
        return f"{self.event_day} - {self.title}"


class DailyConversationSummary(models.Model):
    """일별 LLM 대화 요약 모델"""
    summary_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='daily_conversation_summaries',
        verbose_name='사용자'
    )
    pregnancy = models.ForeignKey(
        Pregnancy,
        on_delete=models.CASCADE,
        related_name='daily_conversation_summaries',
        verbose_name='임신 정보',
        null=True, blank=True
    )
    summary_text = models.TextField(verbose_name='일별 대화 요약 내용')
    conversations = models.ManyToManyField(
        'llm.LLMConversation',
        related_name='daily_summaries',
        verbose_name='관련 대화'
    )
    summary_date = models.DateField(verbose_name='요약 날짜')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '일별 대화 요약'
        verbose_name_plural = '일별 대화 요약 목록'
        ordering = ['-summary_date']
        unique_together = ['user', 'summary_date']  # 사용자별로 날짜당 하나의 요약만 존재

    def __str__(self):
        return f"{self.user.username} - {self.summary_date} 대화 요약"


class BabyDiary(models.Model):
    """아기 일기 모델 - 태교용 일기"""
    diary_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='baby_diaries',
        verbose_name='사용자'
    )
    pregnancy = models.ForeignKey(
        Pregnancy,
        on_delete=models.CASCADE,
        related_name='baby_diaries',
        verbose_name='임신 정보',
        null=True, blank=True
    )
    content = models.TextField(verbose_name='아기 일기 내용')
    diary_date = models.DateField(verbose_name='일기 날짜')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '아기 일기'
        verbose_name_plural = '아기 일기 목록'
        ordering = ['-diary_date']
        unique_together = ['user', 'diary_date']  # 사용자별로 날짜당 하나의 일기만 존재

    def __str__(self):
        return f"{self.user.username} - {self.diary_date} 아기 일기"


class BabyDiaryPhoto(models.Model):
    """태교일기 사진 모델"""
    photo_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # BabyDiary와 1:N 관계 설정
    babydiary = models.ForeignKey(
        'BabyDiary',
        related_name='photos',
        on_delete=models.CASCADE,
        verbose_name='태교일기'
    )

    image = models.ImageField(upload_to='baby_diary_photos/%Y/%m/%d/', verbose_name='사진')
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def thumbnail_url(self):
        """썸네일 URL을 반환합니다."""
        try:
            if not self.image:
                return None
                
            # 이미지 파일이 실제로 존재하는지 확인
            if not os.path.exists(self.image.path):
                print(f"이미지 파일이 존재하지 않음: {self.image.path}")
                return self.image.url if self.image else None
                
            # PIL로 이미지 열기 시도
            try:
                from PIL import Image
                Image.open(self.image.path).verify()  # 이미지가 유효한지 확인
            except Exception as img_verify_error:
                print(f"이미지 파일이 손상되었거나 유효하지 않음: {img_verify_error}")
                return self.image.url if self.image else None
                
            # sorl.thumbnail 사용하여 썸네일 생성
            return get_thumbnail(self.image, '200x200', crop='center', quality=90).url
        except ImportError:
            print("sorl.thumbnail이 설치되지 않았습니다.")
            return self.image.url if self.image else None
        except Exception as e:
            # 썸네일 생성 실패 시 로깅하고 원본 이미지 URL 반환
            print(f"썸네일 생성 오류: {e}")
            try:
                return self.image.url if self.image else None
            except Exception as img_error:
                print(f"원본 이미지 URL 생성 오류: {img_error}")
                return None

    class Meta:
        verbose_name = '태교일기 사진'
        verbose_name_plural = '태교일기 사진 목록'

    def __str__(self):
        return f"{self.babydiary.diary_date} 태교일기 사진"