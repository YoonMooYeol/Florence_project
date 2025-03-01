from rest_framework import serializers
from .models import LLMInteraction

class QuerySerializer(serializers.Serializer):
    """사용자 질문 시리얼라이저"""
    user_id = serializers.CharField(required=True, help_text='사용자 ID')
    query_text = serializers.CharField(required=True, help_text='질문 내용')
    preferences = serializers.JSONField(required=False, default=dict, help_text='사용자 선호 설정')
    
    class Meta:
        fields = ['user_id', 'query_text', 'preferences']

class ResponseSerializer(serializers.Serializer):
    """LLM 응답 시리얼라이저"""
    response = serializers.CharField(help_text='LLM 응답 내용')
    follow_up_questions = serializers.ListField(
        child=serializers.CharField(),
        help_text='후속 질문 제안'
    )
    query_info = serializers.JSONField(help_text='질문 분석 정보')
    
    class Meta:
        fields = ['response', 'follow_up_questions', 'query_info']

class LLMInteractionSerializer(serializers.ModelSerializer):
    """LLM 상호작용 시리얼라이저"""
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = LLMInteraction
        fields = ['id', 'user', 'user_name', 'query', 'response', 'query_type', 'metadata', 'created_at']
    
    def get_user_name(self, obj):
        return obj.user.name if obj.user else 'Anonymous' 