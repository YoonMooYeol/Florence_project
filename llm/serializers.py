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
    
    Example:
        {
            "response": "임신 중 건강한 식단은 다양한 영양소를 균형 있게 섭취하는 것이 중요합니다..."
        }
    """
    response = serializers.CharField(help_text='LLM 응답 내용')
    
    class Meta:
        fields = ['response']
        
    def to_representation(self, instance):
        """직접 dict를 생성하여 성능 최적화"""
        return {
            'response': instance.get('response', '')
        }

class LLMConversationSerializer(serializers.ModelSerializer):
    """
    LLM 대화 시리얼라이저
    
    Fields:
        id (UUID): 대화 ID
        name (str): 사용자 이름
        query (str): 사용자 질문
        response (str): LLM 응답
        user_info (dict): 대화 시점의 사용자 정보
        created_at (datetime): 생성 시간
        updated_at (datetime): 수정 시간
    """
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = LLMConversation
        fields = ['id', 'name', 'query', 'response', 'user_info', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_name(self, obj):
        """사용자 이름 반환 (사용자가 없는 경우 빈 문자열)"""
        if not hasattr(obj, '_cached_name'):
            obj._cached_name = obj.user.name if obj.user else ''
        return obj._cached_name

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