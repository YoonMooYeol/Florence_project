from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

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
