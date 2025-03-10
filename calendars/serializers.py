from rest_framework import serializers
from .models import Event, EventConversationSummary

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

class EventConversationSummarySerializer(serializers.ModelSerializer):
    """일정 대화 요약 시리얼라이저"""
    class Meta:
        model = EventConversationSummary
        fields = '__all__'
        read_only_fields = ['summary_id', 'created_at', 'updated_at']

class EventConversationSummaryDetailSerializer(serializers.ModelSerializer):
    """일정 대화 요약 상세 시리얼라이저"""
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_type = serializers.CharField(source='event.event_type', read_only=True)
    event_day = serializers.DateField(source='event.event_day', read_only=True)
    
    class Meta:
        model = EventConversationSummary
        fields = ['summary_id', 'event', 'event_title', 'event_type', 'event_day', 
                  'summary_text', 'generated_date', 'created_at', 'updated_at']
        read_only_fields = ['summary_id', 'created_at', 'updated_at']

class MonthlyConversationSummarySerializer(serializers.Serializer):
    """월별 대화 요약 시리얼라이저"""
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    event_summaries = EventConversationSummarySerializer(many=True)

class DailyConversationSummarySerializer(serializers.Serializer):
    """일별 대화 요약 시리얼라이저"""
    date = serializers.DateField()
    event_summaries = EventConversationSummarySerializer(many=True)