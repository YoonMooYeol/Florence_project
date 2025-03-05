from rest_framework import serializers
from .models import ConversationSession, Message, Feedback


class UserSerializer(serializers.Serializer):
    """사용자 정보 직렬화"""
    username = serializers.CharField()
    email = serializers.EmailField()


class MessageSerializer(serializers.ModelSerializer):
    """대화 메시지 직렬화"""
    id = serializers.UUIDField(format='hex')
    sender = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'sender', 'content', 'time', 'emotion', 'confidence', 'step', 'created_at']
    
    def get_sender(self, obj):
        return 'user' if obj.answer else 'bot'
    
    def get_content(self, obj):
        return obj.answer if obj.answer else obj.question
    
    def get_time(self, obj):
        return obj.created_at.strftime('%H:%M')


class FeedbackSerializer(serializers.ModelSerializer):
    """피드백 정보 직렬화"""
    id = serializers.UUIDField(format='hex')
    medical_info = serializers.JSONField()
    
    class Meta:
        model = Feedback
        fields = ['id', 'summary', 'emotional_analysis', 'health_tips', 'medical_info', 'created_at']


class ConversationListSerializer(serializers.ModelSerializer):
    """대화 목록용 직렬화"""
    id = serializers.UUIDField(format='hex')
    user = UserSerializer()
    message_count = serializers.SerializerMethodField()
    has_feedback = serializers.SerializerMethodField()
    feedback = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversationSession
        fields = ['id', 'user', 'created_at', 'is_completed', 'message_count', 'has_feedback', 'feedback']
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_has_feedback(self, obj):
        return hasattr(obj, 'feedback')
    
    def get_feedback(self, obj):
        if hasattr(obj, 'feedback'):
            return {
                'summary': obj.feedback.summary,
                'emotional_analysis': obj.feedback.emotional_analysis,
                'health_tips': obj.feedback.health_tips,
                'medical_info': obj.feedback.medical_info
            }
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """대화 상세 정보 직렬화"""
    id = serializers.UUIDField(format='hex')
    user = serializers.CharField(source='user.username')
    messages = MessageSerializer(many=True, read_only=True)
    feedback = FeedbackSerializer(read_only=True)
    
    class Meta:
        model = ConversationSession
        fields = ['id', 'user', 'created_at', 'updated_at', 'is_completed', 'messages', 'feedback']


class HealthcareResponseSerializer(serializers.Serializer):
    """헬스케어 API 응답 직렬화"""
    status = serializers.CharField()
    conversation_id = serializers.UUIDField(format='hex')
    feedback = serializers.CharField()
    medical_info = serializers.JSONField()
    log_messages = serializers.ListField(child=serializers.CharField())
    questions_and_answers = serializers.ListField(child=serializers.DictField())
