from django.contrib import admin
from .models import LLMConversation, ChatManager

@admin.register(ChatManager)
class ChatManagerAdmin(admin.ModelAdmin):
    """채팅방 관리자 설정"""
    list_display = ('chat_id', 'get_user_name', 'topic_preview', 'message_count', 'created_at', 'is_active')
    list_filter = ('created_at', 'is_active')
    search_fields = ('user__name', 'topic')
    readonly_fields = ('chat_id', 'message_count', 'created_at', 'updated_at')
    fieldsets = (
        ('기본 정보', {
            'fields': ('chat_id', 'user', 'pregnancy', 'is_active', 'created_at', 'updated_at')
        }),
        ('채팅 정보', {
            'fields': ('topic', 'message_count')
        }),
    )
    actions = ['summarize_selected_chats']
    
    def get_user_name(self, obj):
        """사용자 이름 반환"""
        return obj.user.name if obj.user else ''
    get_user_name.short_description = '사용자'
    
    def topic_preview(self, obj):
        """주제 미리보기 반환"""
        if not obj.topic:
            return '(요약 없음)'
        return obj.topic[:30] + '...' if len(obj.topic) > 30 else obj.topic
    topic_preview.short_description = '주제'
    
    def summarize_selected_chats(self, request, queryset):
        """선택된 채팅방 요약 액션"""
        for chat in queryset:
            chat.summarize_chat()
        self.message_user(request, f"{queryset.count()}개의 채팅방이 요약되었습니다.")
    summarize_selected_chats.short_description = "선택된 채팅방 요약하기"

@admin.register(LLMConversation)
class LLMConversationAdmin(admin.ModelAdmin):
    """LLM 대화 관리자 설정"""
    list_display = ('id', 'get_user_name', 'query_preview', 'get_chat_room', 'created_at')
    list_filter = ('created_at', 'using_rag')
    search_fields = ('query', 'response', 'user__name')
    readonly_fields = ('id', 'created_at')
    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'user', 'chat_room', 'created_at')
        }),
        ('대화 내용', {
            'fields': ('query', 'response')
        }),
        ('메타데이터', {
            'fields': ('user_info', 'source_documents', 'using_rag'),
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
    
    def get_chat_room(self, obj):
        """채팅방 정보 반환"""
        if not obj.chat_room:
            return '(없음)'
        return str(obj.chat_room.chat_id)
    get_chat_room.short_description = '채팅방'
