from rest_framework import serializers
from .models import Event, DailyConversationSummary, BabyDiary, BabyDiaryPhoto
from llm.models import LLMConversation

class EventSerializer(serializers.ModelSerializer):
    """
    일정 목록 조회용 간략 시리얼라이저
    """
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['event_id', 'created_at', 'updated_at', 'user']

class EventDetailSerializer(serializers.ModelSerializer):
    """
    일정 상세 정보 및 생성/수정용 시리얼라이저
    recurrence_rules JSON 필드를 처리합니다.
    """
    class Meta:
        model = Event
        fields = '__all__'
        read_only_fields = ['event_id', 'created_at', 'updated_at', 'user']
        
    def validate(self, data):
        """
        recurrence_rules 필드 검증 및 구조 확인
        """
        recurrence_rules = data.get('recurrence_rules')
        
        # recurrence_rules이 있는 경우 기본 구조 확인
        if recurrence_rules:
            # 필수 pattern 필드 확인
            if 'pattern' not in recurrence_rules:
                raise serializers.ValidationError({"recurrence_rules": "반복 패턴은 필수 항목입니다."})
            
            # pattern 유효성 검증
            pattern = recurrence_rules.get('pattern')
            valid_patterns = ['daily', 'weekly', 'monthly', 'yearly']
            if pattern not in valid_patterns:
                raise serializers.ValidationError({"recurrence_rules": f"유효한 반복 패턴이 아닙니다. 가능한 값: {', '.join(valid_patterns)}"})
            
            # until 날짜 형식 확인
            until = recurrence_rules.get('until')
            if until:
                try:
                    from datetime import datetime
                    datetime.strptime(until, '%Y-%m-%d')
                except ValueError:
                    raise serializers.ValidationError({"recurrence_rules": "종료일은 YYYY-MM-DD 형식이어야 합니다."})
            
            # exceptions 형식 확인
            exceptions = recurrence_rules.get('exceptions', [])
            if not isinstance(exceptions, list):
                raise serializers.ValidationError({"recurrence_rules": "예외 날짜는 리스트 형태여야 합니다."})
            
            for exception_date in exceptions:
                try:
                    datetime.strptime(exception_date, '%Y-%m-%d')
                except ValueError:
                    raise serializers.ValidationError({"recurrence_rules": "예외 날짜는 YYYY-MM-DD 형식이어야 합니다."})
        
        # start_date 및 end_date 유효성 검증
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if end_date and start_date > end_date:
            raise serializers.ValidationError({"end_date": "종료 날짜는 시작 날짜보다 같거나 이후여야 합니다."})
        
        return data

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
    diary_id = serializers.UUIDField(source="babydiary.diary_id", read_only=True)
    image_thumbnail = serializers.SerializerMethodField()
    
    class Meta:
        model = BabyDiaryPhoto
        fields = ['photo_id', 'diary_id', 'image', 'image_thumbnail', 'created_at']
        read_only_fields = ['photo_id', 'diary_id', 'created_at']
    
    def get_image_thumbnail(self, obj):
        # 모델에 정의된 thumbnail_url 속성 사용
        if obj.image:
            try:
                return obj.thumbnail_url
            except Exception as e:
                # 오류 발생 시 원본 이미지 URL 반환
                return obj.image.url
        return None


class BabyDiarySerializer(serializers.ModelSerializer):
    photos = BabyDiaryPhotoSerializer(many=True, read_only=True)
    class Meta:
        model = BabyDiary
        fields = '__all__'
        read_only_fields = [ 'user', 'created_at', 'updated_at', 'photos', 'diary_date']

class BabyDiaryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BabyDiary
        fields = ['diary_date', 'diary_id']
        read_only_fields = ['diary_id']
        
    def create(self, validated_data):
        return BabyDiary.objects.create(**validated_data)

