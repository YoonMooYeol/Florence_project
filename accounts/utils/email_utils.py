import random
import re

from django.core.cache import cache
from django.core.mail import EmailMessage
from django.conf import settings

from accounts.models import EmailVerification


class EmailUtils:

    EMAIL_NO_WRITE_ERROR = "이메일을 입력하세요."
    EMAIL_INVALID_ERROR = "이메일 주소가 유효하지 않습니다."
    EMAIL_EXISTS_ERROR = "이미 등록된 이메일입니다."
    CODE_EXPIRED_ERROR = "인증 코드가 만료되었습니다."
    CODE_INVALID_ERROR = "잘못된 인증 코드입니다."
    PASSWORD_RESET_ERROR = "비밀번호 재설정 코드 전송에 실패했습니다."

    @staticmethod
    def generate_verification_code():
        return str(random.randint(100000, 999999))

    @staticmethod
    def validate_email(email):
        if not email:
            return False  # 이메일이 비어 있으면 False 반환
        return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))  # 정규식 검증 후 True/False 반환

    @staticmethod
    def get_verification_code(email):
        """이메일로 저장된 인증 코드 가져오기"""
        return cache.get(f"email_code:{email}")

    @staticmethod
    def save_verification_code(email, code):
        cache.set(f"email_code:{email}", code, timeout=600)
        print(f"[DEBUG] 저장된 인증 코드: {cache.get(f'email_code_{email}')}")

    @staticmethod
    def verify_code(email, input_code):
        """ 입력된 인증 코드 확인 """
        stored_code = EmailUtils.get_verification_code(email)
        if not stored_code:
            raise ValueError(EmailUtils.CODE_EXPIRED_ERROR)

        if stored_code != input_code:
            raise ValueError(EmailUtils.CODE_INVALID_ERROR)

        return True

    @staticmethod
    def send_verification_email(email):
        """ 회원가입 시 이메일 인증 코드 전송 """
        if not EmailUtils.validate_email(email):
            raise ValueError(EmailUtils.EMAIL_INVALID_ERROR)

        code = EmailUtils.generate_verification_code()
        EmailUtils.save_verification_code(email, code)

        email = EmailMessage(
            subject="[누리달] 💡이메일 인증 코드 안내 💡",
            body=f"안녕하세요.\n인증 코드는 [{code}]입니다. 10분 안에 인증을 완료해주세요.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        email.send(fail_silently=False)

    @staticmethod
    def send_password_reset_email(email):
        """ 비밀번호 재설정 인증 코드 전송"""
        if not EmailUtils.validate_email(email):
            raise ValueError(EmailUtils.EMAIL_INVALID_ERROR)

        code = EmailUtils.generate_verification_code()
        EmailUtils.save_verification_code(email, code)

        email = EmailMessage(
            subject="[누리달] 💡비밀번호 재설정 인증 코드 안내 💡",
            body="안녕하세요.\n인증 코드는 [{code}]입니다. 10분 안에 인증을 완료해주세요.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        email.send(fail_silently=False)










