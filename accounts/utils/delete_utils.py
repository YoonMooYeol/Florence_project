from accounts.models import Follow, Pregnancy, Photo, User
from calendars.models import BabyDiary, Event, DailyConversationSummary, BabyDiaryPhoto
from llm.models import LLMConversation
from rest_framework_simplejwt.tokens import RefreshToken


class UserDataDeletionService:
    """사용자 관련 데이터 삭제"""

    def __init__(self, user):
        self.user = user

    def delete_related_data(self):
        """유저 관련 데이터 삭제"""
        Follow.objects.filter(following=self.user).delete()
        Follow.objects.filter(follower=self.user).delete()
        BabyDiary.objects.filter(user=self.user).delete()
        Pregnancy.objects.filter(user=self.user).delete()
        Event.objects.filter(user=self.user).delete()
        LLMConversation.objects.filter(user=self.user).delete()
        Photo.objects.filter(user=self.user).delete()
        baby_diary_ids = BabyDiary.objects.filter(user=self.user).values_list('diary_id', flat=True)
        BabyDiaryPhoto.objects.filter(babydiary_id__in=baby_diary_ids).delete()



    def blacklist_tokens(self, request):
        """유저의 JWT 토큰을 블랙리스트에 추가"""
        refresh_token = request.COOKIES.get('refresh_token')  # 프론트에서 쿠키에 저장한 경우
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()  # 블랙리스트에 추가
            except Exception as e:
                print(f"토큰 블랙리스트 추가 실패: {e}")

