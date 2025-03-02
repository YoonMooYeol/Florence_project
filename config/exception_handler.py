from rest_framework.views import exception_handler
from rest_framework.exceptions import NotFound, ValidationError, PermissionDenied, AuthenticationFailed
from django.http import Http404
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db.models import ObjectDoesNotExist

def custom_exception_handler(exc, context):
    """
    REST Framework의 기본 예외 처리기를 커스터마이징하여 한글 오류 메시지를 반환합니다.
    """
    # 기본 예외 처리기 호출
    response = exception_handler(exc, context)
    
    # 예외 유형에 따라 한글 메시지로 변환
    if isinstance(exc, Http404) or isinstance(exc, NotFound):
        if hasattr(exc, 'detail') and exc.detail:
            # 이미 커스텀 메시지가 있는 경우 그대로 사용
            pass
        else:
            # 기본 메시지를 한글로 변환
            if response:
                response.data = {'detail': '요청한 리소스를 찾을 수 없습니다.'}
    
    elif isinstance(exc, ValidationError):
        if response:
            # 유효성 검사 오류 메시지 번역
            if 'detail' in response.data:
                response.data['detail'] = '입력 데이터가 유효하지 않습니다.'
            # 필드별 오류 메시지는 그대로 유지
    
    elif isinstance(exc, PermissionDenied) or isinstance(exc, DjangoPermissionDenied):
        if response:
            response.data = {'detail': '이 작업을 수행할 권한이 없습니다.'}
    
    elif isinstance(exc, AuthenticationFailed):
        if response:
            response.data = {'detail': '인증에 실패했습니다. 올바른 자격 증명을 제공하세요.'}
    
    elif isinstance(exc, ObjectDoesNotExist):
        if response:
            # 모델 이름에 따라 다른 메시지 반환
            model_name = exc.__class__.__name__.replace('DoesNotExist', '')
            if 'User' in model_name:
                response.data = {'detail': '사용자를 찾을 수 없습니다.'}
            elif 'LLMConversation' in model_name:
                response.data = {'detail': '대화를 찾을 수 없습니다.'}
            else:
                response.data = {'detail': f'{model_name}을(를) 찾을 수 없습니다.'}
    
    return response