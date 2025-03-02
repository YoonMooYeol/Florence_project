from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth import get_user_model
import logging
import uuid
import time
import threading
from django.conf import settings
from django.db import connection

from .utils import PyLLMService
from .models import LLMConversation
from .serializers import QuerySerializer, LLMConversationSerializer, LLMConversationEditSerializer, LLMConversationDeleteSerializer

# User 모델 가져오기
User = get_user_model()

# 로깅 설정
logger = logging.getLogger(__name__)

# 헬퍼 함수
def get_user_from_request(request):
    """
    요청에서 사용자 객체를 추출하는 헬퍼 함수
    
    인증된 사용자가 있으면 해당 사용자를 반환하고,
    없으면 요청의 user_id 파라미터를 사용하여 사용자를 조회합니다.
    
    Args:
        request (Request): HTTP 요청 객체
        
    Returns:
        tuple: (User 객체 또는 None, 오류 메시지 또는 None, 상태 코드 또는 None)
    """
    # 인증된 사용자 확인
    if request.user and request.user.is_authenticated:
        user = request.user
        logger.debug(f"인증된 사용자: {user.email}, UUID: {user.user_id}")
        
        # 요청의 user_id와 인증된 사용자의 ID가 다른 경우 경고 로그 기록
        request_user_id = request.query_params.get('user_id')
        if request_user_id and str(user.user_id) != request_user_id:
            logger.warning(f"요청의 user_id({request_user_id})와 인증된 사용자의 ID({user.user_id})가 다릅니다. 인증된 사용자를 사용합니다.")
        
        return user, None, None
    
    # 인증된 사용자가 없는 경우 요청의 user_id 파라미터 확인
    request_user_id = request.query_params.get('user_id')
    if not request_user_id:
        logger.warning("사용자 ID가 제공되지 않았습니다.")
        return None, "사용자 ID가 필요합니다.", status.HTTP_400_BAD_REQUEST
    
    # user_id로 사용자 조회
    try:
        # QuerySerializer를 사용하여 UUID 정규화
        serializer = QuerySerializer(data={'user_id': request_user_id, 'query_text': 'dummy'})
        if not serializer.is_valid(raise_exception=False):
            logger.warning(f"유효하지 않은 UUID 형식: {request_user_id}")
            return None, "유효하지 않은 UUID 형식입니다.", status.HTTP_400_BAD_REQUEST
        
        normalized_uuid = serializer.validated_data['user_id']
        
        # 사용자 조회
        try:
            user = User.objects.get(user_id=normalized_uuid)
            logger.debug(f"사용자 조회 성공: {user.name} ({user.email})")
            return user, None, None
        except User.DoesNotExist:
            logger.warning(f"사용자 ID {normalized_uuid}를 찾을 수 없습니다.")
            return None, "사용자를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND
            
    except Exception as e:
        logger.error(f"사용자 조회 오류: {str(e)}")
        return None, f"사용자 조회 중 오류가 발생했습니다: {str(e)}", status.HTTP_500_INTERNAL_SERVER_ERROR

def get_conversation_by_id(user, conversation_id):
    """
    UUID로 대화를 조회하는 헬퍼 함수
    
    Args:
        user (User): 사용자 객체
        conversation_id (str): 대화 UUID
        
    Returns:
        tuple: (LLMConversation 객체 또는 None, 오류 메시지 또는 None)
    """
    if not conversation_id:
        logger.warning("대화 ID가 제공되지 않았습니다.")
        return None, "대화 ID가 필요합니다."
    
    try:
        # 슬래시 제거 (API 엔드포인트에서 종종 발생)
        if conversation_id.endswith('/'):
            conversation_id = conversation_id.rstrip('/')
            
        # UUID 객체로 변환 시도
        try:
            conversation_uuid = uuid.UUID(conversation_id)
        except ValueError:
            logger.warning(f"유효하지 않은 대화 ID 형식: {conversation_id}")
            return None, "유효하지 않은 대화 ID 형식입니다."
        
        # 대화 조회 - 객체가 없으면 DoesNotExist 예외 발생
        try:
            conversation = LLMConversation.objects.select_related('user').get(id=conversation_uuid, user=user)
            logger.debug(f"대화 조회 성공: {conversation.id}")
            return conversation, None
        except LLMConversation.DoesNotExist:
            logger.warning(f"ID가 {conversation_id}인 대화를 찾을 수 없습니다.")
            return None, f"ID가 {conversation_id}인 대화를 찾을 수 없습니다."
        
    except Exception as e:
        logger.error(f"대화 조회 중 오류 발생: {str(e)}")
        return None, f"대화 조회 중 오류가 발생했습니다: {str(e)}"

class MaternalHealthLLMView(APIView):
    """
    산모 건강 관련 LLM API 뷰
    
    이 뷰는 사용자의 질문을 처리하고 LLM을 통해 산모 건강 관련 정보를 제공합니다.
    사용자 질문, 선호도, 임신 주차 등의 정보를 받아 맞춤형 응답을 생성합니다.
    
    Endpoints:
        POST /v1/llm/ - 사용자 질문 처리 및 응답 생성
        
    Request:
        {
            "user_id": "사용자 UUID",
            "query_text": "사용자 질문",
            "preferences": {
                "response_style": "detailed",  // 응답 스타일 (optional)
                "include_references": true     // 참조 포함 여부 (optional)
            },
            "pregnancy_week": 20  // 임신 주차 (optional)
        }
        
    Response:
        {
            "response": "LLM 응답 내용"
        }
    """
    permission_classes = [IsAuthenticated]  # 테스트를 위해 임시로 인증 비활성화
    
    def post(self, request):
        """
        사용자 질문을 처리하고 LLM 응답을 반환
        
        Args:
            request (Request): HTTP 요청 객체
            format (str, optional): 응답 형식
            
        Returns:
            Response: LLM 응답 또는 오류 메시지
        """
        # 성능 측정 시작
        start_time = time.time()
        
        # 디버깅: 요청 데이터 로깅
        logger.debug(f"요청 데이터: {request.data}")
        
        # 1. 요청 데이터 검증
        serializer = QuerySerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"요청 데이터 검증 실패: {serializer.errors}")
            return Response(
                {"error": "잘못된 요청 형식입니다.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2. 요청 데이터 추출
        validated_data = serializer.validated_data
        request_user_id = validated_data.get('user_id')
        query_text = validated_data.get('query_text')
        preferences = validated_data.get('preferences', {})
        pregnancy_week = validated_data.get('pregnancy_week')
        
        # 3. 인증된 사용자 확인 (Django REST Framework가 자동으로 처리)
        if request.user and request.user.is_authenticated:
            authenticated_user = request.user
            user = authenticated_user
            user_id = str(user.user_id)
            logger.debug(f"인증된 사용자: {authenticated_user.email}, UUID: {authenticated_user.user_id}")
        else:
            # 인증된 사용자도 없고 요청에 user_id도 없는 경우
            return Response(
                {"error": "사용자 ID가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 5. 사용자 정보 준비
        user_info = {
            'name': user.name,
            'email': user.email,
            'is_pregnant': user.is_pregnant,
            'user_id': user_id
        }
        
        # 선호도 및 임신 주차 정보 추가
        user_info.update(preferences)
        if pregnancy_week is not None:
            user_info['pregnancy_week'] = pregnancy_week
        
        try:
            # 6. LLM 서비스 생성 및 호출
            llm_service = PyLLMService()
            result = llm_service.process_query(user_id, query_text, user_info)
            
            # 7. 비동기적으로 대화 저장 (성능 개선)
            save_thread = threading.Thread(target=self._save_conversation, args=(user, query_text, result))
            save_thread.daemon = True
            save_thread.start()
            
            # 8. 응답 직렬화 - 최적화된 직렬화 사용
            response_data = {
                'response': result['response']
            }
            
            # 성능 측정 종료 및 로깅
            processing_time = time.time() - start_time
            logger.info(f"LLM 응답 생성 시간: {processing_time:.2f}초")
            
            # 9. 응답 반환 - 직접 딕셔너리 반환으로 최적화
            return Response(response_data, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"LLM 처리 오류: {str(e)}")
            return Response(
                {"error": "서버 오류가 발생했습니다.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _save_conversation(self, user, query_text, result):
        """
        사용자 대화 저장
        
        Args:
            user (User): 사용자 객체
            query_text (str): 사용자 질문
            result (dict): LLM 응답 결과
            
        Returns:
            None
        """
        try:
            if not user:
                logger.warning("대화 저장 중 사용자 객체가 제공되지 않았습니다.")
                return
            
            # 사용자 정보 및 임신 주차 정보 준비
            user_info = {
                'name': user.name,
                'is_pregnant': user.is_pregnant,
                'user_id': str(user.user_id)  # UUID를 문자열로 변환하여 추가
            }
            
            # 임신 주차 정보가 result에 포함되어 있으면 추가
            if 'user_info' in result and 'pregnancy_week' in result['user_info']:
                user_info['pregnancy_week'] = result['user_info']['pregnancy_week']
            
            # 대화 저장
            conversation = LLMConversation.objects.create(
                user=user,
                query=query_text,
                response=result['response'],
                user_info=user_info
            )
            logger.info(f"대화 저장 완료: {conversation.id}")
            
            # 데이터베이스 연결 닫기 (스레드에서 사용 후)
            connection.close()
            
        except Exception as e:
            logger.error(f"대화 저장 오류: {str(e)}")
            # 대화 저장 실패는 사용자 응답에 영향을 주지 않도록 예외를 전파하지 않음


class LLMConversationViewSet(APIView):
    """
    LLM 대화 관리 API
    
    이 뷰는 사용자의 LLM 대화 기록을 관리하는 기능을 제공합니다.
    대화 조회, 수정, 삭제 등의 작업을 수행할 수 있습니다.
    
    Endpoints:
        GET /v1/llm/conversations/ - 사용자의 대화 기록 조회
        PUT /v1/llm/conversations/edit/ - 대화 수정
        DELETE /v1/llm/conversations/delete/ - 대화 삭제
        
    Query Parameters:
        user_id (str): 사용자 UUID
        conversation_id (str): 대화 UUID (PUT, DELETE에서 사용)
        query_type (str, optional): 질문 유형으로 필터링 (GET에서 사용)
        
    Authentication:
        인증이 필요한 경우 Authorization 헤더를 다음 형식으로 제공해야 합니다:
        Authorization: Bearer <token>
        
        예시:
        Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    permission_classes = [IsAuthenticated]  # 인증 요구사항 일시적으로 완화
    
    def get(self, request, format=None):
        """
        사용자의 LLM 대화 기록 조회
        
        Query Parameters:
            user_id (str): 사용자 UUID (인증된 사용자가 있는 경우 선택적)
            query_type (str, optional): 질문 유형으로 필터링
            
        Returns:
            Response: 대화 목록 또는 오류 메시지
        """
        # 성능 측정 시작
        start_time = time.time()
        
        # 1. 사용자 결정
        user, error, error_status = get_user_from_request(request)
        if not user:
            return Response({"error": error}, status=error_status)
            
        # 2. 쿼리 필터 구성
        query_type = request.query_params.get('query_type')
        filters = {'user': user}
            
        if query_type:
            filters['query_type'] = query_type
        
        # 3. 대화 조회 - select_related 사용하여 N+1 문제 해결
        conversations = LLMConversation.objects.select_related('user').filter(**filters).order_by('-created_at')
        
        # 4. 직렬화
        serializer = LLMConversationSerializer(conversations, many=True)
        
        # 성능 측정 종료 및 로깅
        processing_time = time.time() - start_time
        logger.info(f"대화 목록 조회 시간: {processing_time:.2f}초")
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request, format=None):
        """
        대화 수정
        
        Query Parameters:
            user_id (str): 사용자 UUID (인증된 사용자가 있는 경우 선택적)
            conversation_id (str): 대화 UUID
            index (str, optional): conversation_id와 동일한 기능 (하위 호환성 유지)
            
        Request Body:
            {
                "query": "수정할 질문 내용"
            }
            
        Returns:
            Response: 수정된 대화 또는 오류 메시지
        """
        try:
            # 1. 요청 데이터 검증
            serializer = LLMConversationEditSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"error": "잘못된 요청 형식입니다.", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 2. 사용자 결정
            user, error, error_status = get_user_from_request(request)
            if not user:
                return Response({"error": error}, status=error_status)
            
            # 3. 대화 ID 확인
            conversation_id = request.query_params.get('conversation_id')
            # 하위 호환성을 위해 index 파라미터도 확인
            if not conversation_id:
                conversation_id = request.query_params.get('index')
                
            if not conversation_id:
                return Response(
                    {"error": "대화 ID가 필요합니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 4. 대화 조회
            conversation, error = get_conversation_by_id(user, conversation_id)
            if not conversation:
                logger.warning(f"대화 조회 실패: {error}, conversation_id: {conversation_id}")
                return Response(
                    {"error": error},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 5. 수정할 질문 내용
            new_query = serializer.validated_data.get('query')
            
            # 6. 질문 내용 업데이트
            old_query = conversation.query
            conversation.query = new_query
            
            # 7. 사용자 정보 준비
            user_id_str = str(user.user_id)
            user_info = {
                'name': user.name,
                'is_pregnant': user.is_pregnant,
                'user_id': user_id_str
            }
            
            # 8. LLM 서비스 호출하여 응답 업데이트
            llm_service = PyLLMService()
            result = llm_service.process_query(user_id_str, new_query, user_info)
            
            # 9. 대화 업데이트
            conversation.query = new_query
            conversation.response = result['response']
            conversation.save()
            
            # 10. 응답 직렬화
            response_data = {
                'id': str(conversation.id),
                'user_id': user_id_str,
                'query': conversation.query,
                'response': conversation.response,
                'user_info': conversation.user_info,
                'created_at': conversation.created_at,
                'updated_at': conversation.updated_at
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"대화 수정 오류: {str(e)}")
            return Response(
                {"error": "대화 수정 중 오류가 발생했습니다.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, format=None):
        """
        대화 삭제
        
        Query Parameters:
            user_id (str): 사용자 UUID (인증된 사용자가 있는 경우 선택적)
            conversation_id (str, optional): 삭제할 대화의 ID (UUID 형식)
                                  생략 시 모든 대화 삭제
            index (str, optional): conversation_id와 동일한 기능 (하위 호환성 유지)
                                  
        Request Body:
            {
                "delete_mode": "all" | "query_only"  // 삭제 모드 (기본값: "all")
            }
            
        Returns:
            Response: 삭제 결과 또는 오류 메시지
        """
        try:
            # 1. 사용자 결정
            user, error, error_status = get_user_from_request(request)
            if not user:
                return Response({"error": error}, status=error_status)
            
            # 2. 대화 ID 확인 (없으면 모든 대화 삭제)
            conversation_id = request.query_params.get('conversation_id')
            # 하위 호환성을 위해 index 파라미터도 확인
            if not conversation_id:
                conversation_id = request.query_params.get('index')
                
            if conversation_id is None:
                # 사용자의 모든 대화 삭제
                count = LLMConversation.objects.filter(user=user).count()
                LLMConversation.objects.filter(user=user).delete()
                
                return Response(
                    {"message": f"{count}개의 대화가 삭제되었습니다."},
                    status=status.HTTP_200_OK
                )
            
            # 3. 삭제 모드 확인
            serializer = LLMConversationDeleteSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"error": "잘못된 요청 형식입니다.", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            delete_mode = serializer.validated_data.get('delete_mode', 'all')
            
            # 4. 대화 조회
            conversation, error = get_conversation_by_id(user, conversation_id)
            if not conversation:
                logger.warning(f"대화 조회 실패: {error}, conversation_id: {conversation_id}")
                return Response(
                    {"error": error},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 5. 삭제 모드에 따라 처리
            if delete_mode == 'query_only':
                # 사용자 입력만 삭제 (빈 문자열로 설정)
                conversation.query = ''
                conversation.save()
                response_serializer = LLMConversationSerializer(conversation)
                
                return Response(response_serializer.data, status=status.HTTP_200_OK)
            else:
                # 대화 완전 삭제
                query_type = getattr(conversation, 'query_type', None)
                conversation.delete()
                
                return Response(
                    {"message": "대화가 삭제되었습니다."},
                    status=status.HTTP_200_OK
                )
                
        except Exception as e:
            logger.error(f"대화 삭제 오류: {str(e)}")
            return Response(
                {"error": "대화 삭제 중 오류가 발생했습니다.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )