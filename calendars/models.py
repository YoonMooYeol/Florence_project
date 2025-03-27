from django.db import models
import uuid
from accounts.models import User, Pregnancy
from sorl.thumbnail import get_thumbnail
import os
# PostgreSQL의 JSONField 대신 Django 기본 JSONField 사용
from django.db.models import JSONField



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

    EVENT_COLORS = [
        ('#FFD600', '노랑'),
        ('#FF6B6B', '빨강'),
        ('#4ECDC4', '청록'),
        ('#45B7D1', '하늘'),
        ('#96CEB4', '민트'),
        ('#FFEEAD', '연한 노랑'),
        ('#D4A5A5', '연한 빨강'),
        ('#9B59B6', '보라'),
        ('#3498DB', '파랑'),
        ('#2ECC71', '초록'),
    ]

    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events', verbose_name='사용자')
    title = models.CharField(
        max_length=100, 
        verbose_name='제목',
        error_messages={
            'blank': '제목을 입력해주세요.',
            'max_length': '제목은 100자를 초과할 수 없습니다.'
        }
    )
    description = models.TextField(blank=True, null=True, verbose_name='설명')
    start_date = models.DateField(verbose_name='시작 날짜')
    end_date = models.DateField(verbose_name='종료 날짜', null=True, blank=True)
    start_time = models.TimeField(blank=True, null=True, verbose_name='시작 시간')
    end_time = models.TimeField(blank=True, null=True, verbose_name='종료 시간')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='other', verbose_name='일정 유형')
    recurrence_rules = JSONField(
        null=True, 
        blank=True, 
        verbose_name='반복 규칙',
        help_text='{"pattern": "daily/weekly/monthly/yearly", "until": "2024-12-31", "exceptions": ["2024-06-15"]}'
    )
    event_color = models.CharField(
        max_length=7,
        choices=EVENT_COLORS,
        default='#FFD600',
        verbose_name='일정 색상'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'start_time']
        verbose_name = '일정'
        verbose_name_plural = '일정들'

    def __str__(self):
        return f"{self.start_date} - {self.title}"


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
                
            # 이미지 경로가 있는지 확인
            if not self.image.url:
                print(f"이미지 URL이 존재하지 않음")
                return None
                
            # 서버에 파일이 있는지 확인
            try:
                if not os.path.exists(self.image.path):
                    print(f"이미지 파일이 존재하지 않음: {self.image.path}")
                    return self.image.url
            except Exception as e:
                print(f"이미지 경로 확인 오류: {e}")
                return self.image.url
                
            # sorl.thumbnail 사용하여 썸네일 생성
            try:
                return get_thumbnail(self.image, '200x200', crop='center', quality=90).url
            except Exception as thumb_error:
                print(f"썸네일 생성 실패: {thumb_error}")
                return self.image.url
                
        except Exception as e:
            # 모든 예외 케이스에서 원본 이미지 URL 반환
            print(f"thumbnail_url 속성 오류: {e}")
            try:
                return self.image.url if self.image else None
            except:
                return None

    class Meta:
        verbose_name = '태교일기 사진'
        verbose_name_plural = '태교일기 사진 목록'

    def __str__(self):
        return f"{self.babydiary.diary_date} 태교일기 사진"