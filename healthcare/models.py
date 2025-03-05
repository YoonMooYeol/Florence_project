from django.db import models
from django.conf import settings
import uuid
import json

class ConversationSession(models.Model):
    """사용자와 AI 간의 대화 세션"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Conversation {self.id} - {self.user.username}"

class Message(models.Model):
    """대화 세션 내의 개별 메시지"""
    EMOTION_CHOICES = [
        ('happiness', '행복'),
        ('sadness', '슬픔'),
        ('anger', '분노'),
        ('fear', '두려움'),
        ('surprise', '놀람'),
        ('disgust', '혐오'),
        ('neutral', '중립'),
        ('worry', '걱정'),
        ('anxiety', '불안'),
        ('excitement', '설렘'),
        ('tiredness', '피곤')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ConversationSession, on_delete=models.CASCADE, related_name='messages')
    question = models.TextField()
    answer = models.TextField()
    emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES, default='neutral')
    confidence = models.FloatField(default=0.0)  # 감정 분석 신뢰도
    step = models.IntegerField()  # 대화 단계
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['step']

    def __str__(self):
        return f"Message {self.step} - {self.session.id}"

class Feedback(models.Model):
    """대화 세션에 대한 피드백"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(ConversationSession, on_delete=models.CASCADE, related_name='feedback')
    summary = models.TextField()  # 대화 요약
    emotional_analysis = models.TextField()  # 감정 분석 결과
    health_tips = models.TextField()  # 건강 팁
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 의료 정보 (JSON 형식으로 저장)
    medical_info = models.JSONField(default=dict)
    
    def __str__(self):
        return f"Feedback for {self.session.id}"
    
    def set_tips(self, tips_list):
        """의료 정보 팁 목록을 저장"""
        if 'tips' not in self.medical_info:
            self.medical_info['tips'] = []
        self.medical_info['tips'] = tips_list
        
    def set_sources(self, sources_list):
        """의료 정보 출처 목록을 저장"""
        if 'sources' not in self.medical_info:
            self.medical_info['sources'] = []
        self.medical_info['sources'] = sources_list
