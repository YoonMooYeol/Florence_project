from django.db import models
import uuid
from accounts.models import User, Pregnancy

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