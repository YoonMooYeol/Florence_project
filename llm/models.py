import uuid
from django.db import models
from accounts.models import User

class LLMConversation(models.Model):
    """LLM과의 대화 기록 모델"""
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='llm_conversations',
        null=True,
        blank=True
    )
    query = models.TextField(verbose_name='사용자 질문')
    response = models.TextField(verbose_name='LLM 응답')
    user_info = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name='사용자 정보'
    )
    source_documents = models.JSONField(
        default=list,
        blank=True,
        verbose_name='참조 문서'
    )
    using_rag = models.BooleanField(
        default=False,
        verbose_name='RAG 사용 여부'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='생성 시간'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='수정 시간'
    )
    
    class Meta:
        verbose_name = 'LLM 대화'
        verbose_name_plural = 'LLM 대화 목록'
        ordering = ['-created_at']
    
    def __str__(self):
        """대화의 문자열 표현"""
        user_name = self.user.name if self.user else ''
        return f"{user_name}: {self.query[:30]}..."
