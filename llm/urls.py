from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

"""
LLM 앱 URL 설정

이 모듈은 LLM 앱의 URL 패턴을 정의합니다.
각 URL 패턴은 특정 뷰와 연결되어 있으며, 해당 뷰는 요청을 처리하고 응답을 반환합니다.

URL 패턴:
    /v1/llm/ - 산모 건강 관련 LLM API (POST)
    /v1/llm/conversations/ - 대화 조회 API (GET)
    /v1/llm/conversations/edit/ - 대화 수정 API (PUT)
    /v1/llm/conversations/delete/ - 대화 삭제 API (DELETE)
    /v1/llm/pregnancy-search/ - 임신 주차 검색 API (POST)
    
    # 채팅방 관련 URL
    /v1/llm/chat/rooms/ - 채팅방 목록 조회 (GET) 및 생성 (POST)
    /v1/llm/chat/rooms/<chat_id>/ - 채팅방 상세 정보 조회 (GET)
    /v1/llm/chat/rooms/<chat_id>/messages/ - 채팅방에 메시지 생성 (POST)
    /v1/llm/chat/rooms/<chat_id>/summarize/ - 채팅방 요약 (POST)
"""

app_name = 'llm'

# 라우터 설정
router = DefaultRouter()
router.register(r'conversations', views.LLMConversationViewSet, basename='conversation')

urlpatterns = [
    # LLM 질문 API
    path('', views.LLMQueryView.as_view(), name='llm_query'),
    
    # 임신 주차 검색 API
    path('pregnancy-search/', views.pregnancy_search, name='pregnancy_search'),
    
    # 채팅방 관련 API
    path('chat/rooms/', views.ChatRoomListCreateView.as_view(), name='chat_rooms'),
    path('chat/rooms/<uuid:chat_id>/', views.ChatRoomDetailView.as_view(), name='chat_room_detail'),
    path('chat/rooms/<uuid:chat_id>/messages/', views.ChatMessageCreateView.as_view(), name='chat_message_create'),
    path('chat/rooms/<uuid:chat_id>/summarize/', views.ChatRoomSummarizeView.as_view(), name='chat_room_summarize'),
    
    # 뷰셋 라우터 포함
    path('', include(router.urls)),
] 