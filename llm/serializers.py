from rest_framework import serializers
from .models import LLMConversation

class QuerySerializer(serializers.Serializer):
    user_id = serializers.CharField(required=True)
    query_text = serializers.CharField(required=True)
    preferences = serializers.JSONField(required=False, default=dict)
    pregnancy_week = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        fields = ['user_id', 'query_text', 'preferences', 'pregnancy_week']

class ResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
    
    class Meta:
        fields = ['response']

class LLMConversationSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = LLMConversation
        fields = ['id', 'name', 'query', 'response', 'user_info', 'created_at', 'updated_at']
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