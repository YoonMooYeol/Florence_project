from rest_framework import serializers
from .models import Event, DailyConversationSummary, BabyDiary
from llm.models import LLMConversation

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['event_id', 'created_at', 'updated_at']

class EventDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['event_id', 'created_at', 'updated_at']

class DailyConversationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyConversationSummary
        fields = '__all__'
        read_only_fields = ['summary_id', 'created_at', 'updated_at']

class DailyConversationSummaryCreateSerializer(serializers.ModelSerializer):
    conversation_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True,
        write_only=True
    )
    
    class Meta:
        model = DailyConversationSummary
        fields = ['pregnancy', 'summary_date', 'summary_text', 'conversation_ids']
        read_only_fields = ['user', 'summary_id', 'created_at', 'updated_at']

    def create(self, validated_data):
        conversation_ids = validated_data.pop('conversation_ids')
        summary = DailyConversationSummary.objects.create(**validated_data)
        
        # 관련 대화 연결
        conversations = LLMConversation.objects.filter(id__in=conversation_ids)
        summary.conversations.set(conversations)
        
        return summary

class BabyDiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = BabyDiary
        fields = '__all__'
        read_only_fields = ['diary_id', 'user', 'created_at', 'updated_at']

class BabyDiaryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BabyDiary
        fields = ['pregnancy', 'content', 'diary_date']
        read_only_fields = ['diary_id', 'user', 'created_at', 'updated_at']
        
    def create(self, validated_data):
        return BabyDiary.objects.create(**validated_data)

