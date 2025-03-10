import uuid
import os
import logging
from django.db import models
from accounts.models import User, Pregnancy
from langchain_openai import ChatOpenAI

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
    
    def summarize_chat(self):
        """채팅 내용을 요약하여 topic 필드를 업데이트"""
        # 채팅 내용 가져오기
        messages = LLMConversation.objects.filter(chat_room=self).order_by('created_at')
        
        if not messages.exists():
            return
        
        try:
            # LLM을 사용한 대화 요약 로직
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.error("OpenAI API 키가 설정되지 않았습니다.")
                # 키가 없는 경우 기존 임시 로직 사용
                first_message = messages.first()
                if first_message:
                    self.topic = first_message.query[:50] + "..." if len(first_message.query) > 50 else first_message.query
                    self.save(update_fields=['topic', 'updated_at'])
                return
            
            # 대화 내용 수집
            conversation_text = ""
            for msg in messages:
                conversation_text += f"사용자: {msg.query}\n"
                conversation_text += f"챗봇: {msg.response}\n\n"
            
            # LLM 모델 설정
            model = os.getenv('LLM_MODEL', 'gpt-4o')
            llm = ChatOpenAI(temperature=0.3, model=model)
            
            # 요약 프롬프트 작성
            prompt = f"""
            다음은 임신과 출산에 관련된 대화입니다. 이 대화의 핵심 주제만 가지고 50자 이내로 간결하게 요약해주세요. 
            요약엔 절대로 들어가지 말아야하는 것이 있습니다. "~라는 주제의 챗봇과의 대화"같은 불필요한 것은 넣지말아주세요. 
            생성되지 말아야하는 예시)
            사용자: 오줌이 너무 자주 마려워
            챗봇: 오줌이 너무 자주 마려워라는 주제로 이야기한 챗봇과의 대화입니다.
            
            
            

            {conversation_text}
            
            요약 (50자 이내):
            """
            
            # 응답 생성
            response = llm.invoke(prompt)
            summary = response.content.strip()
            
            # 요약이 너무 길다면 자르기
            if len(summary) > 50:
                summary = summary[:50]
            
            # 요약 적용
            self.topic = summary
            self.save(update_fields=['topic', 'updated_at'])
            logger.info(f"채팅방 {self.chat_id} 요약 완료: {summary}")
            
        except Exception as e:
            logger.error(f"채팅방 요약 중 오류 발생: {str(e)}")
            # 오류 발생 시 기존 임시 로직 사용
            first_message = messages.first()
            if first_message:
                self.topic = first_message.query[:50] + "..." if len(first_message.query) > 50 else first_message.query
                self.save(update_fields=['topic', 'updated_at'])

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
