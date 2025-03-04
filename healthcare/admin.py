from django.contrib import admin
from .models import ConversationSession, Message, Feedback

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('id', 'created_at')
    
class FeedbackInline(admin.StackedInline):
    model = Feedback
    extra = 0
    readonly_fields = ('id', 'created_at')

@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'is_completed')
    list_filter = ('is_completed', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [MessageInline, FeedbackInline]

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'step', 'emotion', 'confidence', 'created_at')
    list_filter = ('emotion', 'created_at')
    search_fields = ('question', 'answer', 'session__user__username')
    readonly_fields = ('id', 'created_at')

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'created_at')
    search_fields = ('summary', 'emotional_analysis', 'health_tips', 'session__user__username')
    readonly_fields = ('id', 'created_at')
    
    def get_medical_info(self, obj):
        return obj.medical_info
    
    get_medical_info.short_description = '의료 정보'
