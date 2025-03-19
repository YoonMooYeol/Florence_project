import uuid
import os
import logging
from django.db import models
from accounts.models import User, Pregnancy

# 로깅 설정
logger = logging.getLogger(__name__)

class ChatManager(models.Model):
    """채팅방 관리 모델"""
    chat_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='채팅 ID'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_rooms',
        verbose_name='사용자'
    )
    pregnancy = models.ForeignKey(
        Pregnancy,
        on_delete=models.SET_NULL,
        related_name='chat_rooms',
        null=True,
        blank=True,
        verbose_name='임신 정보'
    )
    topic = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='채팅 주제 요약'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성 일시'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정 일시'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성 상태'
    )
    message_count = models.IntegerField(
        default=0,
        verbose_name='메시지 수'
    )
    
    class Meta:
        verbose_name = '채팅방'
        verbose_name_plural = '채팅방 목록'
        ordering = ['-created_at']
    
    def __str__(self):
        """채팅방의 문자열 표현"""
        if self.topic:
            return f"{self.topic} ({self.user.name})"
        else:
            return f"채팅 {self.chat_id} ({self.user.name})"

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
    chat_room = models.ForeignKey(
        ChatManager,
        on_delete=models.CASCADE,
        related_name='messages',
        null=True,
        blank=True,
        verbose_name='채팅방'
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
    
    def save(self, *args, **kwargs):
        """저장 후 채팅방의 메시지 수 업데이트"""
        # 일반 저장 로직
        super().save(*args, **kwargs)
        
        # 메시지 저장 후 채팅방의 메시지 수 업데이트
        if self.chat_room:
            self.chat_room.message_count = LLMConversation.objects.filter(chat_room=self.chat_room).count()
            self.chat_room.save(update_fields=['message_count', 'updated_at'])
