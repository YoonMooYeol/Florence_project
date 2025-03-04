from rest_framework import serializers
from .models import EmbeddingFile

class EmbeddingFileSerializer(serializers.ModelSerializer):
    """
    임베딩 파일 정보 직렬화 클래스
    """
    class Meta:
        model = EmbeddingFile
        fields = '__all__'
