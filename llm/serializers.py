from rest_framework import serializers
from .models import LLMConversation

class QuerySerializer(serializers.Serializer):
    """
    사용자 질문 시리얼라이저
    
    Fields:
        user_id (str): 사용자 UUID
        query_text (str): 질문 내용
        preferences (dict): 사용자 선호 설정 (optional)
        pregnancy_week (int): 임신 주차 (1-40) (optional)
    
    Example:
        {
            "user_id": "9fa5edd1-d4be-44bb-a2c7-d3da4f8717bd",
            "query_text": "임신 중 건강한 식단은 어떻게 구성해야 하나요?",
            "preferences": {
                "response_style": "detailed",
                "include_references": true
            },
            "pregnancy_week": 20
        }
    """
    user_id = serializers.CharField(required=True, help_text='사용자 ID')
    query_text = serializers.CharField(required=True, help_text='질문 내용')
    preferences = serializers.JSONField(required=False, default=dict, help_text='사용자 선호 설정')
    pregnancy_week = serializers.IntegerField(required=False, allow_null=True, help_text='임신 주차 (1-40)')
    
    class Meta:
        fields = ['user_id', 'query_text', 'preferences', 'pregnancy_week']

class ResponseSerializer(serializers.Serializer):
    """
    LLM 응답 시리얼라이저
    
    Fields:
        response (str): LLM 응답 내용
        follow_up_questions (list): 후속 질문 제안 목록
        query_info (dict): 질문 분석 정보
    
    Example:
        {
            "response": "임신 중 건강한 식단은 다양한 영양소를 균형 있게 섭취하는 것이 중요합니다...",
            "follow_up_questions": [
                "임신 중 피해야 할 음식은 무엇인가요?",
                "임신 중 필요한 영양제는 어떤 것이 있나요?"
            ],
            "query_info": {
                "query_type": "nutrition",
                "keywords": ["임신", "식단", "영양"]
            }
        }
    """
    response = serializers.CharField(help_text='LLM 응답 내용')
    follow_up_questions = serializers.ListField(
        child=serializers.CharField(),
        help_text='후속 질문 제안'
    )
    query_info = serializers.JSONField(help_text='질문 분석 정보')
    
    class Meta:
        fields = ['response', 'follow_up_questions', 'query_info']

class LLMConversationSerializer(serializers.ModelSerializer):
    """
    LLM 대화 시리얼라이저
    
    Fields:
        id (UUID): 대화 ID
        name (str): 사용자 이름
        query (str): 사용자 질문
        response (str): LLM 응답
        query_type (str): 질문 유형
        metadata (dict): 대화 메타데이터
        created_at (datetime): 생성 시간
    """
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = LLMConversation
        fields = ['id', 'name', 'query', 'response', 'query_type', 'metadata', 'created_at']
    
    def get_name(self, obj):
        """사용자 이름 반환 (사용자가 없는 경우 빈 문자열)"""
        return obj.user.name if obj.user else ''

class LLMConversationEditSerializer(serializers.Serializer):
    """
    LLM 대화 수정 시리얼라이저
    
    Fields:
        query (str): 수정할 질문 내용
    
    Example:
        {
            "query": "수정된 질문 내용"
        }
    """
    query = serializers.CharField(required=True, help_text='수정할 질문 내용')
    
    class Meta:
        fields = ['query']

class LLMConversationDeleteSerializer(serializers.Serializer):
    """
    LLM 대화 삭제 시리얼라이저
    
    Fields:
        delete_mode (str): 삭제 모드
            - 'all': 모두 삭제 (기본값)
            - 'query_only': 질문만 삭제
    
    Example:
        {
            "delete_mode": "all"
        }
    """
    delete_mode = serializers.ChoiceField(
        choices=['all', 'query_only'],
        default='all',
        help_text='삭제 모드 (all: 모두 삭제, query_only: 질문만 삭제)'
    )
    
    class Meta:
        fields = ['delete_mode'] 