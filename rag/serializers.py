from rest_framework import serializers
from .models import RAG, RAG_DB

class RAGSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = RAG
        fields = ['id', 'user', 'user_name', 'question', 'answer', 'created_at', 'updated_at']
    
    def get_user_name(self, obj):
        if obj.user:
            return obj.user.name
        return None

class RAGDBSerializer(serializers.ModelSerializer):
    class Meta:
        model = RAG_DB
        fields = ['id', 'file_name', 'file_path', 'created_at', 'updated_at']
