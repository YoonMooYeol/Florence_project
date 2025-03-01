import uuid
from django.db import models
from accounts.models import User

class LLMInteraction(models.Model):
    """LLM과의 상호작용 기록 모델"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='llm_interactions', null=True, blank=True)
    query = models.TextField(verbose_name='사용자 질문')
    response = models.TextField(verbose_name='LLM 응답')
    query_type = models.CharField(max_length=50, verbose_name='질문 유형', default='general')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='메타데이터')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시간')
    
    class Meta:
        verbose_name = 'LLM 상호작용'
        verbose_name_plural = 'LLM 상호작용 목록'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.name if self.user else 'Anonymous'}: {self.query[:30]}..."
