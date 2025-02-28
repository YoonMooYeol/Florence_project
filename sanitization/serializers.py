from rest_framework import serializers
from .models import UserSession, Interaction, PregnancyResource

class UserSessionSerializer(serializers.ModelSerializer):
    """사용자 세션 모델 직렬화기"""
    
    class Meta:
        model = UserSession
        fields = '__all__'


class InteractionSerializer(serializers.ModelSerializer):
    """사용자 상호작용 모델 직렬화기"""
    
    class Meta:
        model = Interaction
        fields = '__all__'


class PregnancyResourceSerializer(serializers.ModelSerializer):
    """임신 리소스 모델 직렬화기"""
    
    class Meta:
        model = PregnancyResource
        fields = '__all__'


class QuerySerializer(serializers.Serializer):
    """사용자 쿼리 직렬화기"""
    user_id = serializers.CharField(required=True, help_text="사용자 ID")
    query_text = serializers.CharField(required=True, help_text="질문 내용")
    pregnancy_week = serializers.IntegerField(required=False, help_text="임신 주차 (선택사항)")
    preferences = serializers.DictField(required=False, default={}, help_text="사용자 설정")


class ResponseSerializer(serializers.Serializer):
    """LLM 응답 직렬화기"""
    response = serializers.CharField(help_text="LLM 응답")
    follow_up_questions = serializers.ListField(
        child=serializers.CharField(),
        help_text="후속 질문 제안"
    )
    query_info = serializers.DictField(help_text="쿼리 분석 정보")
    
    def to_representation(self, instance):
        """응답에서 필요한 정보만 포함"""
        data = super().to_representation(instance)
        
        # 분석 결과는 클라이언트에 불필요하므로 제외
        if "analysis_results" in instance:
            del instance["analysis_results"]
            
        return data 