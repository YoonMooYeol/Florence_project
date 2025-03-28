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
from .agent_loop import get_agent_loop

from .models import LLMConversation, ChatManager
from .serializers import (
    QuerySerializer, ResponseSerializer, LLMConversationSerializer,
    LLMConversationEditSerializer, LLMConversationDeleteSerializer,
    ChatRoomSerializer, ChatRoomCreateSerializer, ChatRoomListSerializer, 
    ChatMessageCreateSerializer, ChatRoomSummarizeSerializer,
    # LLMAgentQuerySerializer, LLMAgentResponseSerializer
)
from accounts.models import Pregnancy  # Pregnancy 모델 임포트
from accounts.models import User


from dotenv import load_dotenv
from .openai_agent import openai_agent_service, PregnancyContext, Runner  # OpenAI 에이전트 서비스 임포트

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

class OpenAIAgentStreamView(APIView):
    """
    ThreadPoolExecutor를 사용하여 비동기-동기 컨텍스트 전환 문제를 해결한 SSE 스트리밍 뷰
    """

    permission_classes = [AllowAny]

    def _event_stream(self, request):
        """실시간 스트리밍 SSE 이벤트"""
        import json
        import asyncio
        import threading
        
        # 파라미터 추출
        query_text = request.data.get("query_text")
        user_id = request.data.get("user_id")
        
        # 인증 토큰 추출
        auth_header = request.headers.get('Authorization')
        auth_token = None
        if auth_header and auth_header.startswith("Bearer "):
            auth_token = auth_header.split(" ")[1]
            print(f"뷰: 인증 토큰 추출됨 (길이: {len(auth_token)})")
        else:
            print("뷰: Authorization 헤더 없거나 Bearer 토큰 아님.")
        
        if not query_text or not user_id:
            yield f"data: {json.dumps({'error': 'query_text와 user_id는 필수입니다.'})}\n\n"
            return
        
        # 시작 메시지
        yield f"data: {json.dumps({'status': 'start'})}\n\n"
        
        # 스레드간 데이터 큐
        from queue import Queue
        chunk_queue = Queue()
        stop_event = threading.Event()
        
        def worker():
            """별도 스레드에서 비동기 처리 실행"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def stream_processor():
                try:
                    # 에이전트 스트림 설정 - auth_token 전달
                    stream_result = await openai_agent_service.process_query(
                        query_text=query_text,
                        user_id=user_id,
                        thread_id=request.data.get("thread_id"),
                        auth_token=auth_token,  # 인증 토큰 전달
                        pregnancy_week=request.data.get("pregnancy_week"),
                        baby_name=request.data.get("baby_name"),
                        stream=True
                    )
                    
                    # 실시간으로 큐에 추가
                    accumulated_response = ""
                    
                    print(f"스트림 응답 시작: needs_verification={getattr(stream_result, 'needs_verification', 'undefined')}")
                    
                    async for event in stream_result.stream_events():
                        if event.type == "raw_response_event" and hasattr(event.data, 'delta'):
                            accumulated_response += event.data.delta
                            chunk_queue.put({"delta": event.data.delta, "complete": False})
                        elif event.type == "tool_start":
                            chunk_queue.put({"tool": event.data.name, "status": "start"})
                        elif event.type == "tool_end":
                            chunk_queue.put({"tool": event.data.name, "status": "end"})
                        elif event.type == "handoff":
                            chunk_queue.put({
                                "handoff": True, 
                                "from": event.data.from_agent, 
                                "to": event.data.to_agent
                            })
                    
                    # 대화 저장
                    context = PregnancyContext(user_id=user_id, thread_id=request.data.get("thread_id"))
                    await context.save_to_db_async(query_text, accumulated_response)
                    
                    # 검증이 필요한 경우 스트리밍 후 검증 수행
                    if hasattr(stream_result, 'needs_verification') and stream_result.needs_verification:
                        print(f"검증 필요: 응답 길이 = {len(accumulated_response)} 글자")
                        # 검증 진행 중임을 알림
                        chunk_queue.put({"verification_status": "start"})
                        
                        try:
                            # 데이터 검증 에이전트 실행
                            verification_agent = openai_agent_service.get_data_verification_agent(context)
                            print("검증 에이전트 생성 완료")
                            
                            verification_result = await Runner.run(
                                verification_agent,
                                accumulated_response,
                                context=context
                            )
                            print("검증 실행 완료")
                            
                            # 검증 결과 저장 및 전송
                            validation_result = verification_result.final_output
                            context.add_verification_result(validation_result)
                            
                            print(f"검증 결과: is_accurate={validation_result.is_accurate}, score={validation_result.confidence_score}")
                            
                            # 검증 결과 전송
                            chunk_queue.put({
                                "verification_status": "complete",
                                "verification": {
                                    "is_accurate": validation_result.is_accurate,
                                    "confidence_score": validation_result.confidence_score,
                                    "reason": validation_result.reason,
                                    "corrected_information": validation_result.corrected_information
                                }
                            })
                        except Exception as e:
                            print(f"검증 과정에서 오류 발생: {str(e)}")
                            chunk_queue.put({
                                "verification_status": "error",
                                "error": str(e)
                            })
                    else:
                        print("검증이 필요하지 않습니다")
                    
                    # 완료 메시지
                    chunk_queue.put({
                        "response": accumulated_response,
                        "complete": True
                    })
                    chunk_queue.put({"status": "done"})
                except Exception as e:
                    print(f"스트림 프로세서 오류: {str(e)}")
                    chunk_queue.put({"error": str(e)})
                    chunk_queue.put({"status": "done"})
                finally:
                    stop_event.set()  # 작업 완료 신호
            
            # 비동기 처리 실행
            loop.run_until_complete(stream_processor())
        
        # 스레드 시작
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
        
        # 메인 스레드에서 큐 소비 및 실시간 전송
        while not (stop_event.is_set() and chunk_queue.empty()):
            try:
                chunk = chunk_queue.get(timeout=0.1)
                yield f"data: {json.dumps(chunk)}\n\n"
                chunk_queue.task_done()
            except Exception:
                # 큐가 비었지만 작업이 아직 진행 중인 경우 대기
                pass

    def post(self, request):
        """
        동기 View + StreamingHttpResponse 로 SSE 응답
        """
        response = StreamingHttpResponse(
            self._event_stream(request),
            content_type='text/event-stream'
        )
        response['X-Accel-Buffering'] = 'no'
        response['Cache-Control'] = 'no-cache'
        return response