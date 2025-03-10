from rest_framework import serializers
from .models import LLMConversation, ChatManager

class QuerySerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)
    query_text = serializers.CharField(required=True)
    preferences = serializers.JSONField(required=False, default=dict)
    pregnancy_week = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        fields = ['user_id', 'query_text', 'preferences', 'pregnancy_week']

class ResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
    source_documents = serializers.ListField(required=False, default=list)
    using_rag = serializers.BooleanField(required=False, default=False)
    
    class Meta:
        fields = ['response', 'source_documents', 'using_rag']

class LLMConversationSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = LLMConversation
        fields = ['id', 'name', 'query', 'response', 'user_info', 'source_documents', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_name(self, obj):
        if obj.user:
            return obj.user.name
        elif obj.user_info and 'name' in obj.user_info:
            return obj.user_info.get('name', '')
        else:
            return ''

class LLMConversationEditSerializer(serializers.Serializer):
    query = serializers.CharField(required=True)
    
    class Meta:
        fields = ['query']

class LLMConversationDeleteSerializer(serializers.Serializer):
    delete_mode = serializers.ChoiceField(
        choices=['all', 'query_only'],
        default='all'
    )
    
    class Meta:
        fields = ['delete_mode']

# 채팅 관련 시리얼라이저
class ChatMessageCreateSerializer(serializers.Serializer):
    """채팅방에서 메시지 생성 시리얼라이저"""
    query = serializers.CharField(required=True)
    
    class Meta:
        fields = ['query']

class ChatRoomMessageSerializer(serializers.ModelSerializer):
    """채팅방 메시지 시리얼라이저"""
    class Meta:
        model = LLMConversation
        fields = ['id', 'query', 'response', 'source_documents', 'using_rag', 'created_at']
        read_only_fields = ['id', 'created_at']

class ChatRoomSerializer(serializers.ModelSerializer):
    """채팅방 시리얼라이저"""
    messages = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatManager
        fields = ['chat_id', 'user', 'user_name', 'topic', 'pregnancy', 'message_count', 'is_active', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['chat_id', 'message_count', 'created_at', 'updated_at']
    
    def get_messages(self, obj):
        """최근 메시지 5개를 가져옵니다"""
        recent_messages = obj.messages.all().order_by('-created_at')[:5]
        return ChatRoomMessageSerializer(recent_messages, many=True).data
    
    def get_user_name(self, obj):
        if obj.user:
            return obj.user.name
        return ""

class ChatRoomCreateSerializer(serializers.ModelSerializer):
    """채팅방 생성 시리얼라이저"""
    class Meta:
        model = ChatManager
        fields = ['user', 'pregnancy', 'is_active']
        
class ChatRoomListSerializer(serializers.ModelSerializer):
    """채팅방 목록 시리얼라이저"""
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatManager
        fields = ['chat_id', 'user', 'user_name', 'topic', 'message_count', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['chat_id', 'message_count', 'created_at', 'updated_at']
    
    def get_user_name(self, obj):
        if obj.user:
            return obj.user.name
        return ""
        
class ChatRoomSummarizeSerializer(serializers.Serializer):
    """채팅방 요약 시리얼라이저"""
    topic = serializers.CharField(read_only=True)
    message_count = serializers.IntegerField(read_only=True)
    is_updated = serializers.BooleanField(read_only=True)
    
    class Meta:
        fields = ['topic', 'message_count', 'is_updated']

class LLMAgentQuerySerializer(serializers.Serializer):
    """LLM 에이전트 질문 시리얼라이저"""
    user_id = serializers.CharField(required=True)
    query_text = serializers.CharField(required=True)
    
    class Meta:
        fields = ['user_id', 'query_text']

class LLMAgentResponseSerializer(serializers.Serializer):
    """LLM 에이전트 응답 시리얼라이저"""
    response = serializers.CharField()
    search_results = serializers.ListField(required=False, default=list)
    search_queries = serializers.ListField(required=False, default=list)
    
    class Meta:
        fields = ['response', 'search_results', 'search_queries'] 