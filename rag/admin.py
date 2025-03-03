from django.contrib import admin
from .models import EmbeddingFile

@admin.register(EmbeddingFile)
class EmbeddingFileAdmin(admin.ModelAdmin):
    """
    임베딩 파일 정보 관리 어드민
    """
    list_display = ['file_name', 'file_path', 'created_at', 'updated_at']
    search_fields = ['file_name', 'file_path']
    list_filter = ['created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
