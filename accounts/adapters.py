from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
import random
import string

class CustomAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        # 기본 이름을 이메일 주소에서 추출
        user.name = user.email.split('@')[0]
        if commit:
            user.save()
        return user

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        
        # 소셜 계정 정보에서 이름 가져오기
        if sociallogin.account.provider == 'kakao':
            kakao_account = sociallogin.account.extra_data.get('kakao_account', {})
            profile = kakao_account.get('profile', {})
            user.name = profile.get('nickname', '')
        elif sociallogin.account.provider == 'naver':
            user.name = sociallogin.account.extra_data.get('name', '')
        
        return user
    
    def get_unique_username(self, email, provider):
        """이메일을 기반으로 간결한 사용자 이름 생성"""
        base_username = email.split('@')[0]
        
        # 기본 길이 제한 (15자)
        if len(base_username) > 15:
            base_username = base_username[:15]
            
        # 랜덤 문자 5개 추가해서 고유성 보장
        random_string = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(5))
        return f"{base_username}_{provider[:3]}_{random_string}"
    
    def save_user(self, request, sociallogin, form=None):
        """소셜 로그인 사용자 저장 시 간결한 사용자 이름 설정"""
        user = sociallogin.user
        
        # 사용자 이름이 너무 길면 줄이기
        if len(user.username) > 30:  # 기본 사용자 이름이 너무 길다면
            email = user.email
            provider = sociallogin.account.provider
            user.username = self.get_unique_username(email, provider)
            
        # 표준 저장 절차 계속 진행
        return super().save_user(request, sociallogin, form)
