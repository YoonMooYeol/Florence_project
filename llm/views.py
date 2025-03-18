from rest_framework.response import Response
from rest_framework import status, viewsets, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import Http404, JsonResponse, StreamingHttpResponse
import logging
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
import json
import asyncio

from .utils import process_llm_query
from .models import LLMConversation, ChatManager
from .serializers import (
    QuerySerializer, ResponseSerializer, LLMConversationSerializer,
    LLMConversationEditSerializer, LLMConversationDeleteSerializer,
    ChatRoomSerializer, ChatRoomCreateSerializer, ChatRoomListSerializer, 
    ChatMessageCreateSerializer, ChatRoomSummarizeSerializer,
    # LLMAgentQuerySerializer, LLMAgentResponseSerializer
)
from accounts.models import Pregnancy  # Pregnancy 모델 임포트
from langchain_community.document_loaders import JSONLoader
from langchain_community.retrievers import TFIDFRetriever
from langchain.chains import RetrievalQA
from .rag_service import rag_service, query_by_pregnancy_week, RAGService  # RAG 서비스 직접 임포트
from accounts.models import User

# 추가 import
import os
# from langchain_openai import ChatOpenAI
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain.agents import AgentExecutor, create_react_agent
# from langchain.prompts import ChatPromptTemplate
# from langchain_community.tools import TavilySearchResults
from dotenv import load_dotenv
from .openai_agent import openai_agent_service, PregnancyContext  # OpenAI 에이전트 서비스 임포트

load_dotenv()

# User 모델 가져오기
User = get_user_model()

# 로깅 설정
logger = logging.getLogger(__name__)

# 커스텀 get_object_or_404 함수
def custom_get_object_or_404(klass, *args, **kwargs):
    """
    한글 오류 메시지를 반환하는 get_object_or_404 함수
    """
    try:
        return klass.objects.get(*args, **kwargs)
    except klass.DoesNotExist:
        if klass == User:
            raise Http404("사용자를 찾을 수 없습니다.")
        elif klass == LLMConversation:
            raise Http404("대화를 찾을 수 없습니다.")
        else:
            raise Http404("요청한 객체를 찾을 수 없습니다.")

class LLMQueryView(generics.GenericAPIView):
    """LLM 질문 처리 API - 제네릭 뷰 버전"""
    serializer_class = QuerySerializer
    permission_classes = [AllowAny]
    
    def post(self, request):
        """LLM 질문 처리"""
        # 요청 데이터 검증
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        # 사용자 조회
        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            # POST 요청이므로 data에서 user_id 가져오기
            user_id = request.data.get('user_id')
            if not user_id:
                return Response({"error": "사용자 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
                
            try:
                user = custom_get_object_or_404(User, user_id=user_id)
            except Http404 as e:
                logger.error(f"사용자 조회 중 오류: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        # 요청 데이터 추출
        query_text = serializer.validated_data['query_text']
        pregnancy_week = serializer.validated_data.get('pregnancy_week')
        
        # 사용자 정보 구성
        user_info = {
            'name': user.name,
            'is_pregnant': user.is_pregnant,
        }
        
        # 임신 정보 가져오기
        pregnancy_info = Pregnancy.objects.filter(user=user).first()
        if pregnancy_info and pregnancy_info.current_week:
            user_info['pregnancy_week'] = pregnancy_info.current_week
        # 요청에서 전달된 pregnancy_week가 있으면 이를 우선 사용
        elif pregnancy_week is not None:
            user_info['pregnancy_week'] = pregnancy_week
        
        # 이전 대화 기록은 사용하지 않음
        chat_history = []
        
        try:
            # LLM 서비스 호출 (이전 대화 기록 없이)
            result = process_llm_query(
                user_id=str(user.user_id),
                query_text=query_text,
                user_info=user_info,
                chat_history=chat_history
            )
            
            # 대화 저장
            LLMConversation.objects.create(
                user=user, 
                query=query_text, 
                response=result['response'], 
                user_info=user_info
            )
            
            return Response(result)
        
        except Exception as e:
            logger.error(f"LLM 처리 중 오류: {str(e)}")
            return Response(
                {"error": "요청 처리 중 오류가 발생했습니다."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LLMConversationViewSet(viewsets.ModelViewSet):
    """LLM 대화 관리 API - 뷰셋 버전"""
    serializer_class = LLMConversationSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """현재 사용자의 대화 목록 반환"""
        # 인증된 사용자 확인
        if self.request.user and self.request.user.is_authenticated:
            user = self.request.user
        else:
            # GET 요청이므로 query_params에서 user_id 가져오기
            user_id = self.request.query_params.get('user_id')
            if not user_id:
                return LLMConversation.objects.none()
                
            try:
                user = custom_get_object_or_404(User, user_id=user_id)
            except Http404:
                return LLMConversation.objects.none()
            
        return LLMConversation.objects.filter(user=user).order_by('-created_at')
    
    def get_object(self):
        """대화 객체 조회 - 권한 확인 포함"""
        # 대화 ID 확인
        conversation_id = self.request.query_params.get('conversation_id') # or self.request.query_params.get('index')
        if not conversation_id:
            return None
        
        # 대화 조회
        try:
            conversation = custom_get_object_or_404(LLMConversation, id=conversation_id)
        except Http404 as e:
            self.permission_denied(self.request, message=str(e))
            return None
        
        # 사용자 권한 확인
        if self.request.user and self.request.user.is_authenticated:
            user = self.request.user
        else:
            # HTTP 메서드에 따라 적절한 곳에서 user_id 가져오기
            if self.request.method in ['GET', 'DELETE']:
                user_id = self.request.query_params.get('user_id')
            else:  # POST, PUT, PATCH
                user_id = self.request.data.get('user_id')
                
            if not user_id:
                self.permission_denied(self.request, message="사용자 ID가 필요합니다.")
                return None
                
            try:
                user = custom_get_object_or_404(User, user_id=user_id)
            except Http404 as e:
                self.permission_denied(self.request, message=str(e))
                return None
            
        # 사용자 권한 확인
        if conversation.user and conversation.user != user:
            self.permission_denied(self.request, message="접근 권한이 없습니다.")
            
        return conversation
    
    @action(detail=False, methods=['get'])
    def list_conversations(self, request):
        """사용자의 대화 목록 조회"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'])
    def edit(self, request):
        """대화 수정"""
        # 요청 데이터 검증
        serializer = LLMConversationEditSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        # 대화 조회
        conversation = self.get_object()
        if not conversation:
            return Response({"error": "대화 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 사용자 조회
        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            # PUT 요청이므로 data에서 user_id 가져오기
            user_id = request.data.get('user_id')
            if not user_id:
                return Response({"error": "사용자 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
                
            try:
                user = custom_get_object_or_404(User, user_id=user_id)
            except Http404 as e:
                logger.error(f"사용자 조회 중 오류: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        # 수정할 질문 내용
        new_query = serializer.validated_data.get('query')
        
        try:
            # LLM 서비스 호출
            result = process_llm_query(
                user_id=str(user.user_id),
                query_text=new_query,
                user_info={'name': user.name, 'is_pregnant': user.is_pregnant}
            )
            
            # 대화 업데이트
            conversation.query = new_query
            conversation.response = result['response']
            conversation.save()
            
            return Response(LLMConversationSerializer(conversation).data)
            
        except Exception as e:
            logger.error(f"대화 수정 중 오류: {str(e)}")
            return Response(
                {"error": "대화 수정 중 오류가 발생했습니다."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['delete'])
    def delete(self, request):
        """대화 삭제"""
        # 사용자 조회
        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            # DELETE 요청이므로 query_params에서 user_id 가져오기
            user_id = request.query_params.get('user_id')
            if not user_id:
                return Response({"error": "사용자 ID가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
                
            try:
                user = custom_get_object_or_404(User, user_id=user_id)
            except Http404 as e:
                logger.error(f"사용자 조회 중 오류: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        
        # 대화 ID 확인
        conversation_id = request.query_params.get('conversation_id') # or request.query_params.get('index')
        
        # 모든 대화 삭제 요청인 경우
        if conversation_id is None:
            count = LLMConversation.objects.filter(user=user).count()
            LLMConversation.objects.filter(user=user).delete()
            return Response({"message": f"{count}개의 대화가 삭제되었습니다."})
        
        # 특정 대화 조회
        conversation = self.get_object()
        if not conversation:
            return Response({"error": "대화를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        
        # 삭제 모드 확인
        serializer = LLMConversationDeleteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        delete_mode = serializer.validated_data.get('delete_mode', 'all')
        
        # 삭제 모드에 따라 처리
        if delete_mode == 'query_only':
            conversation.query = ''
            conversation.save()
            return Response(LLMConversationSerializer(conversation).data)
        else:
            conversation.delete()
            return Response({"message": "대화가 삭제되었습니다."})

@api_view(['POST'])
@permission_classes([AllowAny])
def pregnancy_search(request):
    """임신 주차 기반 검색 API"""
    # 요청 데이터 검증
    if 'query_text' not in request.data or 'pregnancy_week' not in request.data:
        return Response({"error": "query_text와 pregnancy_week가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
    
    query_text = request.data['query_text']
    try:
        pregnancy_week = int(request.data['pregnancy_week'])
    except (ValueError, TypeError):
        return Response({"error": "pregnancy_week는 정수여야 합니다."}, status=status.HTTP_400_BAD_REQUEST)
    
    # 사용자 정보 구성
    user_info = {
        'pregnancy_week': pregnancy_week
    }
    
    try:
        # 직접 query_by_pregnancy_week 함수 호출
        logger.info(f"임신 {pregnancy_week}주차 검색 시작: '{query_text}'")
        
        # 문서 검색 (직접 호출)
        documents = query_by_pregnancy_week(query_text, pregnancy_week)
        
        # 문서가 없으면 빈 응답 반환
        if not documents:
            logger.warning(f"임신 {pregnancy_week}주차 관련 문서를 찾을 수 없습니다.")
            return Response({
                "response": f"임신 {pregnancy_week}주차 관련 정보를 찾을 수 없습니다.",
                "source_documents": [],
                "using_rag": True
            })
        
        # RAGService 인스턴스 생성하여 응답 생성
        rag = RAGService()
        response_text = rag._generate_response_from_docs(documents, query_text)
        
        # 소스 문서 정보 생성
        source_documents = []
        for doc in documents:
            source_documents.append({
                "content": doc.page_content,
                "metadata": doc.metadata
            })
        
        # 응답 구성
        result = {
            "response": response_text,
            "source_documents": source_documents,
            "using_rag": True
        }
        
        logger.info(f"임신 {pregnancy_week}주차 검색 결과: {len(source_documents)}개 문서")
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"임신 주차 검색 중 오류: {str(e)}")
        logger.exception("상세 오류:")
        return Response(
            {"error": "요청 처리 중 오류가 발생했습니다."}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def get_filtered_response(request):
    query = request.GET.get('query', '')
    
    # JSONLoader를 통해 문서를 불러옵니다.
    loader = JSONLoader(file_path='path/to/WeeklyPregnancyInformation.json')
    documents = loader.load()
    
    # 임의의 TF-IDF 기반 리트리버 (또는 다른 리트리버)를 사용해 문서를 검색합니다.
    retriever = TFIDFRetriever.from_documents(documents)
    
    # 12주차와 관련된 문서만 선택하도록 검색 쿼리 수정 (예: "임신 12주차")
    filtered_query = f"임신 {query}" if query.isdigit() else query
    
    results = retriever.get_relevant_documents(filtered_query)
    
    # 이후 요약 체인 또는 응답 체인을 활용해 결과를 정제합니다.
    qa_chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)
    answer = qa_chain.run(filtered_query)
    
    return JsonResponse({
        'query': query,
        'filtered_query': filtered_query,
        'answer': answer,
        'documents': [doc.metadata for doc in results]
    })

class ChatRoomListCreateView(APIView):
    """채팅방 목록 조회 및 생성 API"""
    permission_classes = [AllowAny]  # 실제 구현 시 IsAuthenticated로 변경
    
    def get(self, request):
        """사용자의 채팅방 목록 조회"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({"error": "user_id가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            user = get_object_or_404(User, user_id=user_id)
            chat_rooms = ChatManager.objects.filter(user=user, is_active=True).order_by('-updated_at')
            serializer = ChatRoomListSerializer(chat_rooms, many=True)
            return Response(serializer.data)
        except Http404:
            return Response({"error": "사용자를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"채팅방 목록 조회 중 오류: {str(e)}")
            return Response({"error": "요청 처리 중 오류가 발생했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        """새 채팅방 생성"""
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "user_id가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            user = get_object_or_404(User, user_id=user_id)
            
            # 임신 정보 가져오기
            pregnancy = None
            pregnancy_id = request.data.get('pregnancy_id')
            if pregnancy_id:
                pregnancy = get_object_or_404(Pregnancy, pregnancy_id=pregnancy_id, user=user)
            else:
                # 사용자의 가장 최근 임신 정보 가져오기
                pregnancy = Pregnancy.objects.filter(user=user).order_by('-created_at').first()
            
            # 채팅방 생성
            chat_room = ChatManager.objects.create(
                user=user,
                pregnancy=pregnancy,
                is_active=True
            )
            
            serializer = ChatRoomSerializer(chat_room)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Http404:
            return Response({"error": "사용자 또는 임신 정보를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"채팅방 생성 중 오류: {str(e)}")
            return Response({"error": f"요청 처리 중 오류가 발생했습니다: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
class ChatRoomDetailView(APIView):
    """채팅방 상세 정보 및 메시지 조회 API"""
    permission_classes = [AllowAny]  # 실제 구현 시 IsAuthenticated로 변경
    
    def get(self, request, chat_id):
        """채팅방 상세 정보 및 메시지 조회"""
        try:
            chat_room = get_object_or_404(ChatManager, chat_id=chat_id)
            
            # 메시지 포함 여부 확인
            include_messages = request.query_params.get('include_messages', 'true').lower() == 'true'
            
            if include_messages:
                # 모든 메시지 포함
                serializer = ChatRoomSerializer(chat_room)
                data = serializer.data
                
                # 메시지 가져오기 (시간순 정렬)
                messages = chat_room.messages.all().order_by('created_at')
                message_serializer = LLMConversationSerializer(messages, many=True)
                data['all_messages'] = message_serializer.data
                
                return Response(data)
            else:
                # 메시지 없이 기본 정보만 반환
                serializer = ChatRoomListSerializer(chat_room)
                return Response(serializer.data)
        except Http404:
            return Response({"error": "채팅방을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"채팅방 상세 조회 중 오류: {str(e)}")
            return Response({"error": "요청 처리 중 오류가 발생했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatMessageCreateView(APIView):
    """채팅방에서 메시지 생성 API"""
    permission_classes = [AllowAny]  # 실제 구현 시 IsAuthenticated로 변경
    
    def post(self, request, chat_id):
        """LLM과 대화하기"""
        serializer = ChatMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            chat_room = get_object_or_404(ChatManager, chat_id=chat_id)
            
            # 사용자 정보 구성
            user_info = {}
            if chat_room.user:
                user_info['name'] = chat_room.user.name
            
            # 임신 정보 추가
            if chat_room.pregnancy and chat_room.pregnancy.current_week:
                user_info['pregnancy_week'] = chat_room.pregnancy.current_week
                
            # LLM 질의
            result = rag_service.query(
                query_text=serializer.validated_data['query'],
                user_context=user_info
            )
            
            # 대화 내용 저장
            conversation = LLMConversation.objects.create(
                user=chat_room.user,
                chat_room=chat_room,
                query=serializer.validated_data['query'],
                response=result['response'],
                user_info=user_info,
                source_documents=result.get('source_documents', []),
                using_rag=result.get('using_rag', False)
            )
            
            # ChatManager 업데이트 자동 처리 (save 메서드에서)
            
            # 응답 반환
            response_data = {
                'id': conversation.id,
                'query': conversation.query,
                'response': conversation.response,
                'source_documents': conversation.source_documents,
                'using_rag': conversation.using_rag,
                'created_at': conversation.created_at
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Http404:
            return Response({"error": "채팅방을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"메시지 생성 중 오류: {str(e)}")
            logger.exception("상세 오류")
            return Response({"error": f"요청 처리 중 오류가 발생했습니다: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ChatRoomSummarizeView(APIView):
    """채팅방 대화 요약 API"""
    permission_classes = [AllowAny]  # 실제 구현 시 IsAuthenticated로 변경
    
    def post(self, request, chat_id):
        """채팅방 대화 요약"""
        try:
            chat_room = get_object_or_404(ChatManager, chat_id=chat_id)
            
            # 요약 전 기존 토픽 저장
            previous_topic = chat_room.topic
            
            # LLM을 사용한 대화 요약 처리
            # ChatManager.summarize_chat() 메서드는 이제 LLM을 사용하여 채팅 내용을 50자 이내로 요약합니다.
            chat_room.summarize_chat()
            
            # 응답 데이터 구성
            response_data = {
                'topic': chat_room.topic,
                'message_count': chat_room.message_count,
                'is_updated': previous_topic != chat_room.topic
            }
            
            serializer = ChatRoomSummarizeSerializer(response_data)
            
            return Response(serializer.data)
            
        except Http404:
            return Response({"error": "채팅방을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"채팅방 요약 중 오류: {str(e)}")
            return Response({"error": f"요청 처리 중 오류가 발생했습니다: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# LLMAgentQueryView 및 FlorenceAgentView 대신 OpenAI 에이전트 뷰로 대체
class OpenAIAgentQueryView(generics.GenericAPIView):
    """
    OpenAI 에이전트 API
    
    이 API는 OpenAI 에이전트를 사용하여 임신 관련 질문에 답변합니다.
    산모 건강, 태아 발달, 정부 정책, 영양, 운동 등 다양한 영역의 질문을 처리합니다.
    """
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class OpenAIAgentQuerySerializer(serializers.Serializer):
            user_id = serializers.CharField(required=True, help_text="사용자 ID")
            query_text = serializers.CharField(required=True, help_text="사용자 질문")
            baby_name = serializers.CharField(required=False, help_text="태아 이름", allow_blank=True)
            pregnancy_week = serializers.IntegerField(required=False, help_text="임신 주차", allow_null=True)
            thread_id = serializers.CharField(required=False, help_text="대화 스레드 ID", allow_blank=True)
            stream = serializers.BooleanField(required=False, default=False, help_text="스트리밍 응답 여부")
            
        return OpenAIAgentQuerySerializer
    
    async def _process_query(self, query_data):
        """비동기로 에이전트 쿼리 처리"""
        return await openai_agent_service.process_query(
            query_text=query_data["query_text"],
            user_id=query_data["user_id"],
            thread_id=query_data.get("thread_id"),
            pregnancy_week=query_data.get("pregnancy_week"),
            baby_name=query_data.get("baby_name"),
            stream=query_data.get("stream", False)
        )
    
    def _event_stream(self, stream_result):
        """이벤트 스트림 생성기"""
        try:
            # 스트리밍 초기 응답
            yield f"data: {json.dumps({'status': 'start'})}\n\n"
            
            # 누적 응답 저장
            accumulated_response = ""
            
            # 비동기 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def process_stream():
                nonlocal accumulated_response
                
                async for event in stream_result.stream_events():
                    # 텍스트 이벤트 처리
                    if event.type == "raw_response_event":
                        if hasattr(event.data, 'delta') and event.data.delta:
                            accumulated_response += event.data.delta
                            yield f"data: {json.dumps({'delta': event.data.delta, 'complete': False})}\n\n"
                    
                    # 도구 사용 이벤트 처리
                    elif event.type == "tool_start":
                        yield f"data: {json.dumps({'tool': event.data.name, 'status': 'start'})}\n\n"
                    
                    elif event.type == "tool_end":
                        yield f"data: {json.dumps({'tool': event.data.name, 'status': 'end'})}\n\n"
                    
                    # 핸드오프 이벤트 처리
                    elif event.type == "handoff":
                        yield f"data: {json.dumps({'handoff': True, 'from': event.data.from_agent, 'to': event.data.to_agent})}\n\n"
            
                # 완료 이벤트
                yield f"data: {json.dumps({'response': accumulated_response, 'complete': True})}\n\n"
            
            # 스트림 처리 실행
            for chunk in loop.run_until_complete(process_stream()):
                yield chunk
                
            # 루프 종료
            loop.close()
            
        except Exception as e:
            logger.error(f"스트리밍 처리 중 오류: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        finally:
            # 종료 이벤트
            yield f"data: {json.dumps({'status': 'done'})}\n\n"
    
    def post(self, request):
        """OpenAI 에이전트 API 엔드포인트"""
        try:
            # 요청 데이터 검증
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # 검증된 데이터 추출
            query_data = serializer.validated_data
            logger.info(f"에이전트 쿼리: '{query_data['query_text']}' (user_id: {query_data['user_id']})")
            
            # 스트리밍 응답 여부 확인
            is_stream = query_data.get("stream", False)
            
            if is_stream:
                # 비동기 이벤트 루프 생성
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # 에이전트 실행
                stream_result = loop.run_until_complete(self._process_query(query_data))
                loop.close()
                
                # 스트리밍 응답 생성
                response = StreamingHttpResponse(
                    self._event_stream(stream_result),
                    content_type='text/event-stream'
                )
                response['X-Accel-Buffering'] = 'no'
                response['Cache-Control'] = 'no-cache'
                return response
            else:
                # 일반 응답
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self._process_query(query_data))
                loop.close()
                
                return Response(result, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"에이전트 API 오류: {str(e)}")
            logger.exception("상세 오류:")
            return Response(
                {"error": "서버 오류가 발생했습니다. 나중에 다시 시도해주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OpenAIAgentStreamView(APIView):
    """
    OpenAI 에이전트 스트리밍 API
    
    이 API는 스트리밍 방식으로 OpenAI 에이전트 응답을 제공합니다.
    SSE(Server-Sent Events) 방식으로 실시간 응답을 클라이언트에 전송합니다.
    """
    permission_classes = [AllowAny]
    
    async def _process_query(self, query_data):
        """비동기로 에이전트 쿼리 처리"""
        return await openai_agent_service.process_query(
            query_text=query_data["query_text"],
            user_id=query_data["user_id"],
            thread_id=query_data.get("thread_id"),
            pregnancy_week=query_data.get("pregnancy_week"),
            baby_name=query_data.get("baby_name"),
            stream=True
        )
    
    def _event_stream(self, request):
        """이벤트 스트림 생성기"""
        try:
            # 요청 데이터 추출
            query_text = request.data.get("query_text")
            user_id = request.data.get("user_id")
            thread_id = request.data.get("thread_id")
            pregnancy_week = request.data.get("pregnancy_week")
            baby_name = request.data.get("baby_name")
            
            if not query_text or not user_id:
                yield f"data: {json.dumps({'error': 'query_text와 user_id는 필수입니다.'})}\n\n"
                return
            
            # 쿼리 데이터 구성
            query_data = {
                "query_text": query_text,
                "user_id": user_id,
                "thread_id": thread_id,
                "pregnancy_week": pregnancy_week,
                "baby_name": baby_name
            }
            
            # 스트리밍 초기 응답
            yield f"data: {json.dumps({'status': 'start'})}\n\n"
            
            # 누적 응답 저장
            accumulated_response = ""
            
            # 비동기 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 에이전트 실행
            stream_result = loop.run_until_complete(self._process_query(query_data))
            
            # 응답 스트리밍
            async def process_stream():
                nonlocal accumulated_response
                
                async for event in stream_result.stream_events():
                    # 텍스트 이벤트 처리
                    if event.type == "raw_response_event":
                        if hasattr(event.data, 'delta') and event.data.delta:
                            accumulated_response += event.data.delta
                            yield f"data: {json.dumps({'delta': event.data.delta, 'complete': False})}\n\n"
                    
                    # 도구 사용 이벤트 처리
                    elif event.type == "tool_start":
                        yield f"data: {json.dumps({'tool': event.data.name, 'status': 'start'})}\n\n"
                    
                    elif event.type == "tool_end":
                        yield f"data: {json.dumps({'tool': event.data.name, 'status': 'end'})}\n\n"
                    
                    # 핸드오프 이벤트 처리
                    elif event.type == "handoff":
                        yield f"data: {json.dumps({'handoff': True, 'from': event.data.from_agent, 'to': event.data.to_agent})}\n\n"
            
                # 대화 저장
                context = PregnancyContext(user_id=user_id, thread_id=thread_id)
                conversation = context.save_to_db(query_text, accumulated_response)
                
                # 완료 이벤트
                complete_data = {
                    'response': accumulated_response, 
                    'complete': True
                }
                if conversation:
                    complete_data['conversation_id'] = conversation.id
                
                yield f"data: {json.dumps(complete_data)}\n\n"
            
            # 스트림 처리 실행
            for chunk in loop.run_until_complete(process_stream()):
                yield chunk
                
            # 루프 종료
            loop.close()
            
        except Exception as e:
            logger.error(f"스트리밍 처리 중 오류: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        finally:
            # 종료 이벤트
            yield f"data: {json.dumps({'status': 'done'})}\n\n"
    
    def post(self, request):
        """스트리밍 응답 생성"""
        # SSE 응답 반환
        response = StreamingHttpResponse(
            self._event_stream(request),
            content_type='text/event-stream'
        )
        response['X-Accel-Buffering'] = 'no'
        response['Cache-Control'] = 'no-cache'
        return response