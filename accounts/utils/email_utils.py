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

        subject = "[누리달] 💡이메일 인증 코드 안내 💡"

        body = f"""
        <html>
<body style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">
    <h2 style="color: #333;">안녕하세요.</h2>
    <p style="font-size: 16px; color: #555;">아래 인증 코드를 입력하여 이메일 인증을 완료해주세요.</p>
    
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
            <td align="center">
                <div style="background-color: #f0f8ff; padding: 15px; border-radius: 10px; width: 100%; max-width: 300px;">
                    <span style="font-size: 24px; font-weight: bold; color: #4682B4; white-space: nowrap;">{code}</span>
                </div>
            </td>
        </tr>
    </table>

    <p style="font-size: 14px; color: #777; margin-top: 10px;">인증 코드는 10분 동안 유효합니다.</p>

    <p style="font-size: 14px; color: #999;">
        문의 사항이 있으시면 
<a href="mailto:noorimoon2025@gmail.com" style="color: #4682B4; text-decoration: none;">noorimoon2025@gmail.com</a>
        으로 연락 부탁드려요 :)
    </p>
    
    <p style="font-size: 14px; color: #999;">감사합니다.</p>
</body>
</html>

    """

        email_message = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )

        email_message.content_subtype = "html"
        email_message.send(fail_silently=False)

    @staticmethod
    def send_password_reset_email(email):
        """ 비밀번호 재설정 인증 코드 전송"""
        if not EmailUtils.validate_email(email):
            raise ValueError(EmailUtils.EMAIL_INVALID_ERROR)

        code = EmailUtils.generate_verification_code()
        EmailUtils.save_verification_code(email, code)

        subject = "[누리달] 💡비밀번호 재설정 인증 코드 안내 💡"

        body = f"""
        <html>
<body style="font-family: Arial, sans-serif; text-align: center; padding: 20px;">
    <h2 style="color: #333;">안녕하세요.</h2>
    <p style="font-size: 16px; color: #555;">아래 인증 코드를 입력하여 비밀번호 재설정을 완료해주세요.</p>
    
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
            <td align="center">
                <div style="background-color: #f0f8ff; padding: 15px; border-radius: 10px; width: 100%; max-width: 300px;">
                    <span style="font-size: 24px; font-weight: bold; color: #4682B4; white-space: nowrap;">{code}</span>
                </div>
            </td>
        </tr>
    </table>

    <p style="font-size: 14px; color: #777; margin-top: 10px;">인증 코드는 10분 동안 유효합니다.</p>

    <p style="font-size: 14px; color: #999;">
        문의 사항이 있으시면 
<a href="mailto:noorimoon2025@gmail.com" style="color: #4682B4; text-decoration: none;">noorimoon2025@gmail.com</a>
        으로 연락 부탁드려요 :)
    </p>
    
    <p style="font-size: 14px; color: #999;">감사합니다.</p>
</body>
</html>

    """

        email_message = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )

        email_message.content_subtype = "html"
        email_message.send(fail_silently=False)











