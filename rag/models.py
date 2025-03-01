from django.db import models
from accounts.models import User

# Create your models here.
class RAG(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rag_queries", null=True, blank=True)
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question

# 임베딩된 데이터 저장 테이블
class RAG_DB(models.Model):
    file_name = models.CharField(max_length=200)
    file_path = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.file_name
    
