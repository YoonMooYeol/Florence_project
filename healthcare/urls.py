from django.urls import path
from .views import (
    HealthcareView, 
    ConversationListView, 
    ConversationDetailView,
    NextQuestionView,
    AnswerView
)

urlpatterns = [
    path('', HealthcareView.as_view(), name='healthcare'),
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/<str:conversation_id>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<str:conversation_id>/next-question/', NextQuestionView.as_view(), name='next-question'),
    path('conversations/<str:conversation_id>/answer/', AnswerView.as_view(), name='answer'),
]
