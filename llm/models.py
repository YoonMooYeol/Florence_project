import uuid
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from accounts.models import User

class LLMConversation(models.Model):
    """
    LLM과의 대화 기록 모델
    
    사용자와 LLM 간의 대화 내용을 저장하는 모델입니다.
    각 대화는 사용자 질문, LLM 응답, 사용자 정보 등을 포함합니다.
    
    Fields:
        id (UUID): 대화 고유 식별자
        query (str): 사용자 질문 내용
        response (str): LLM 응답 내용
        user_info (dict): 대화 시점의 사용자 정보
        created_at (datetime): 대화 생성 시간
        updated_at (datetime): 대화 수정 시간
    
    User Info Example:
        {
            "name": "홍길동",
            "is_pregnant": true,
            "pregnancy_week": 20
        }
    """
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="대화 고유 식별자 (UUID)"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='llm_conversations',
        help_text="대화를 생성한 사용자",
        db_index=True
    )
    query = models.TextField(
        verbose_name='사용자 질문',
        help_text="사용자가 입력한 질문 내용"
    )
    response = models.TextField(
        verbose_name='LLM 응답',
        help_text="LLM이 생성한 응답 내용"
    )
    user_info = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name='사용자 정보',
        help_text="대화 시점의 사용자 정보 (임신 여부, 임신 주차 등)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='생성 시간',
        help_text="대화가 생성된 시간",
        db_index=True
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='수정 시간',
        help_text="대화가 마지막으로 수정된 시간"
    )
    
    class Meta:
        verbose_name = 'LLM 대화'
        verbose_name_plural = 'LLM 대화 목록'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        """대화의 문자열 표현 (사용자 이름 + 질문 앞부분)"""
        return f"{self.user.name if self.user else ''}: {self.query[:30]}..."
