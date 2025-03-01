from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import User
import uuid

class CustomJWTAuthentication(JWTAuthentication):
    """커스텀 JWT 인증 클래스"""
    
    def get_user(self, validated_token):
        """
        토큰에서 사용자 ID를 추출하여 사용자 객체를 반환
        """
        try:
            user_id = validated_token.get('user_id')
            
            if not user_id:
                return None
            
            # UUID 문자열을 UUID 객체로 변환
            user_id_uuid = uuid.UUID(user_id)
            
            # 사용자 조회
            user = User.objects.get(user_id=user_id_uuid)
            
            return user
        except User.DoesNotExist:
            return None
        except (ValueError, TypeError):
            return None 