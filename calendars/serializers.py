from rest_framework import serializers
from .models import Event, DailyConversationSummary, BabyDiary, BabyDiaryPhoto
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


class BabyDiaryPhotoSerializer(serializers.ModelSerializer):
    diary_id = serializers.UUIDField(source="BabyDiary.diary_id", read_only=True)

    class Meta:
        model = BabyDiaryPhoto
        fields = ['photo_id', 'diary_id', 'image', 'created_at']
        read_only_fields = ['photo_id', 'diary_id' ,'created_at']


class BabyDiarySerializer(serializers.ModelSerializer):
    photos = BabyDiaryPhotoSerializer(many=True, read_only=True)
    class Meta:
        model = BabyDiary
        fields = '__all__'
        read_only_fields = ['diary_id', 'user', 'created_at', 'updated_at', 'photos']

class BabyDiaryCreateSerializer(serializers.ModelSerializer):
    pregnancy_id = serializers.UUIDField()

    class Meta:
        model = BabyDiary
        fields = ['diary_date','diary_id','pregnancy_id']
        read_only_fields = ['diary_id', 'user', 'created_at', 'updated_at']
        
    def create(self, validated_data):
        return BabyDiary.objects.create(**validated_data)

