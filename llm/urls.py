from django.urls import path, re_path
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
"""

app_name = 'llm'

urlpatterns = [
    # 산모 건강 관련 LLM API
    # POST: 사용자 질문 처리 및 응답 생성
    path('', views.MaternalHealthLLMView.as_view(), name='llm_api'),
    
    # 대화 조회 API
    # GET: 사용자의 대화 기록 조회
    # 파라미터: user_id, query_type(optional)
    re_path(r'^conversations/?$', views.LLMConversationViewSet.as_view(), name='llm_conversations_api'),
    
    # 대화 수정 API
    # PUT: 사용자 입력 수정 및 LLM 응답 업데이트
    # 파라미터: user_id, conversation_id
    re_path(r'^conversations/edit/?$', views.LLMConversationViewSet.as_view(), name='llm_conversation_edit_api'),
    
    # 대화 삭제 API
    # DELETE: 대화 삭제
    # 파라미터: user_id, conversation_id(optional)
    re_path(r'^conversations/delete/?$', views.LLMConversationViewSet.as_view(), name='llm_conversation_delete_api'),
] 