from django.db import models
import uuid

class EmbeddingFile(models.Model):
    """
    임베딩 처리된 파일 정보 모델
    
    이 모델은 임베딩 처리된 파일의 정보를 저장합니다.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255, help_text="파일 이름")
    file_path = models.CharField(max_length=1000, help_text="파일 경로")
    created_at = models.DateTimeField(auto_now_add=True, help_text="생성일")
    updated_at = models.DateTimeField(auto_now=True, help_text="수정일")
    
    def __str__(self):
        return f"{self.file_name} ({self.created_at.strftime('%Y-%m-%d')})"
    
    class Meta:
        verbose_name = "임베딩 파일"
        verbose_name_plural = "임베딩 파일"
    
