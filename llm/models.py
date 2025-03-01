import uuid
from django.db import models
from accounts.models import User

class LLMConversation(models.Model):
    """
    LLM과의 대화 기록 모델
    
    사용자와 LLM 간의 대화 내용을 저장하는 모델입니다.
    각 대화는 사용자 질문, LLM 응답, 질문 유형, 메타데이터 등을 포함합니다.
    
    Fields:
        id (UUID): 대화 고유 식별자
        user (User): 대화를 생성한 사용자 (null 가능)
        query (str): 사용자 질문 내용
        response (str): LLM 응답 내용
        query_type (str): 질문 유형 (예: general, nutrition, medical)
        metadata (dict): 대화 관련 추가 정보 (키워드, 후속 질문, 사용자 정보 등)
        created_at (datetime): 대화 생성 시간
    
    Metadata Example:
        {
            "keywords": ["임신", "영양", "식단"],
            "follow_up_questions": ["임신 중 피해야 할 음식은?", "필요한 영양제는?"],
            "user_info": {
                "name": "홍길동",
                "is_pregnant": true,
                "pregnancy_week": 20
            }
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
        null=True, 
        blank=True,
        help_text="대화를 생성한 사용자 (null 가능)"
    )
    query = models.TextField(
        verbose_name='사용자 질문',
        help_text="사용자가 입력한 질문 내용"
    )
    response = models.TextField(
        verbose_name='LLM 응답',
        help_text="LLM이 생성한 응답 내용"
    )
    query_type = models.CharField(
        max_length=50, 
        verbose_name='질문 유형', 
        default='general',
        help_text="질문의 유형 (예: general, nutrition, medical)"
    )
    metadata = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name='메타데이터',
        help_text="대화 관련 추가 정보 (키워드, 후속 질문, 사용자 정보 등)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='생성 시간',
        help_text="대화가 생성된 시간"
    )
    
    class Meta:
        verbose_name = 'LLM 대화'
        verbose_name_plural = 'LLM 대화 목록'
        ordering = ['-created_at']
    
    def __str__(self):
        """대화의 문자열 표현 (사용자 이름 + 질문 앞부분)"""
        return f"{self.user.name if self.user else ''}: {self.query[:30]}..."
