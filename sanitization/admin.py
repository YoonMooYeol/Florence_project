from django.contrib import admin
from .models import UserSession, Interaction, PregnancyResource

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """사용자 세션 관리자"""
    list_display = ('user_id', 'pregnancy_week', 'last_interaction')
    search_fields = ('user_id',)
    list_filter = ('pregnancy_week',)


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    """사용자 상호작용 관리자"""
    list_display = ('session', 'query_type', 'query', 'created_at')
    search_fields = ('query', 'response')
    list_filter = ('query_type', 'created_at')


@admin.register(PregnancyResource)
class PregnancyResourceAdmin(admin.ModelAdmin):
    """임신 리소스 관리자"""
    list_display = ('week', 'label', 'last_updated')
    search_fields = ('label', 'resource_uri')
    list_filter = ('week',)
