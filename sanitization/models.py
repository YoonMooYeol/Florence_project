from django.db import models
from django.utils import timezone

class UserSession(models.Model):
    """사용자 세션을 관리하는 모델"""
    user_id = models.CharField(max_length=100, unique=True, help_text="고유 사용자 ID")
    pregnancy_week = models.IntegerField(null=True, blank=True, help_text="임신 주차")
    last_interaction = models.DateTimeField(default=timezone.now, help_text="마지막 상호작용 시간")
    preferences = models.JSONField(default=dict, help_text="사용자 설정 (JSON)")
    
    def __str__(self):
        return f"사용자: {self.user_id}, 임신 {self.pregnancy_week}주차"
    
    class Meta:
        verbose_name = "사용자 세션"
        verbose_name_plural = "사용자 세션"


class Interaction(models.Model):
    """사용자 상호작용 내역을 저장하는 모델"""
    session = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name="interactions")
    query = models.TextField(help_text="사용자 질문")
    response = models.TextField(help_text="시스템 응답")
    query_type = models.CharField(max_length=50, help_text="질문 유형")
    metadata = models.JSONField(default=dict, help_text="메타데이터 (JSON)")
    created_at = models.DateTimeField(default=timezone.now, help_text="생성 시간")
    
    def __str__(self):
        return f"{self.session.user_id}의 질문: {self.query[:30]}..."
    
    class Meta:
        verbose_name = "상호작용"
        verbose_name_plural = "상호작용"
        ordering = ['-created_at']


class PregnancyResource(models.Model):
    """임신 주차별 리소스 정보를 캐싱하는 모델"""
    resource_uri = models.CharField(max_length=255, unique=True, help_text="리소스 URI")
    week = models.IntegerField(help_text="임신 주차")
    label = models.CharField(max_length=100, help_text="리소스 레이블")
    data = models.JSONField(help_text="리소스 데이터 (JSON)")
    last_updated = models.DateTimeField(default=timezone.now, help_text="마지막 업데이트 시간")
    
    def __str__(self):
        return f"임신 {self.week}주차: {self.label}"
    
    class Meta:
        verbose_name = "임신 리소스"
        verbose_name_plural = "임신 리소스"
        ordering = ['week']
