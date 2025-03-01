from django.contrib import admin
from .models import LLMConversation

@admin.register(LLMConversation)
class LLMConversationAdmin(admin.ModelAdmin):
    """LLM 대화 관리자 설정"""
    list_display = ('id', 'get_user_name', 'query_type', 'query_preview', 'created_at')
    list_filter = ('query_type', 'created_at')
    search_fields = ('query', 'response', 'user__name')
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'user', 'query_type', 'created_at')
        }),
        ('대화 내용', {
            'fields': ('query', 'response')
        }),
        ('메타데이터', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def get_user_name(self, obj):
        """사용자 이름 반환"""
        return obj.user.name if obj.user else ''
    get_user_name.short_description = '사용자'
    
    def query_preview(self, obj):
        """질문 미리보기 반환"""
        return obj.query[:30] + '...' if len(obj.query) > 30 else obj.query
    query_preview.short_description = '질문'
