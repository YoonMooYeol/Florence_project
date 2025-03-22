from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from django.utils.timezone import now
import uuid
import datetime
import os




class User(AbstractUser):

    """사용자 모델"""
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name='아이디',
        error_messages={
            'unique': "이미 사용 중인 아이디입니다.",
            'max_length': "아이디는 100자를 초과할 수 없습니다.",
            'blank': "아이디를 입력해주세요.",
        }
    )
    email = models.EmailField(
        unique=True, 
        verbose_name='이메일',
        error_messages={
            'unique': "이미 사용 중인 이메일입니다.",
            'invalid': "올바른 이메일 형식이 아닙니다.",
            'blank': "이메일을 입력해주세요.",
        }
    )

    def __str__(self):
        return self.username or self.email

    name = models.CharField(max_length=100, verbose_name='이름')
    phone_number = models.CharField(
        max_length=15, 
        unique=True,
        blank=True,
        verbose_name='전화번호',
        error_messages={
            'unique': "이미 등록된 전화번호입니다.",
            'max_length': "전화번호는 15자를 초과할 수 없습니다.",
            'invalid': "올바른 전화번호 형식이 아닙니다.",
        }
    )
    gender = models.CharField(
        max_length=10, 
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], 
        blank=True, 
        null=True,
        verbose_name='성별'
    )
    is_pregnant = models.BooleanField(default=False, verbose_name='임신 여부')
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name='주소')
    
    USERNAME_FIELD= 'email'
    REQUIRED_FIELDS = ['username', 'name']
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
    
    def __str__(self):
        return self.name

    # 관련된 필드들에 대해 related_name 다르게 설정
    groups = models.ManyToManyField(
        Group, related_name='user_groups', blank=True, help_text='이 사용자가 속한 그룹들.'
    )
    user_permissions = models.ManyToManyField(
        Permission, related_name='user_permissions', blank=True, help_text='이 사용자의 권한들.'
    )

    reset_code = models.CharField(max_length=6, blank=True, null=True)
    reset_code_end = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.name

    # 추가
    def send_reset_code(self, reset_code, end_minutes=10):
        """ 재설정 코드 및 만료 시간 설정 """

        self.reset_code = reset_code
        self.reset_code_end = timezone.now() + datetime.timedelta(minutes=end_minutes)
        self.save()


    def check_reset_code(self, reset_code):
        """ 코드 일치 & 만료 확인 """
        # 코드가 일치하는지 확인
        is_match = self.reset_code == reset_code

    # 만료 시간 확인 (reset_code_end가 None이 아니라면)
        if self.reset_code_end:
            is_expired = timezone.now() > self.reset_code_end
        else:
            is_expired = False

        return is_match and not is_expired

    def clear_reset_code(self):
        """ 만료 코드 및 시간 초기화 """
        self.reset_code = None
        self.reset_code_end = None
        self.save()

    # related_name 충돌 방지를 위해 기존 필드를 수정
        groups = models.ManyToManyField(
            Group, related_name='info_user_groups', blank=True, help_text='이 사용자가 속한 그룹들.'
        )
        user_permissions = models.ManyToManyField(
            Permission, related_name='info_user_permissions', blank=True, help_text='이 사용자의 권한들.'
        )



class Pregnancy(models.Model):
    """임신 정보 모델"""
    pregnancy_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pregnancies')
    husband_id = models.UUIDField(null=True, blank=True)
    baby_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='태명')
    due_date = models.DateField(null=True, blank=True, verbose_name='출산 예정일')
    current_week = models.IntegerField(null=True, blank=True, verbose_name='현재 임신 주차')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    high_risk = models.BooleanField(default=False, verbose_name='고위험 임신 여부')

    class Meta:
        verbose_name = '임신 정보'
        verbose_name_plural = '임신 정보'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.name}님의 임신 정보"

class EmailVerification(models.Model):
    """ 회원가입 인증 모델"""
    email = models.EmailField(unique=True)  # 이메일 주소
    code = models.CharField(max_length=6)  # 인증 코드
    created_at = models.DateTimeField(auto_now_add=True)  # 생성 시간
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        """인증 코드가 5분이 지나면 만료"""
        return (now() - self.created_at).seconds > 300  # 300초 = 5분


class Follow(models.Model):
    """ follower - following 관계 저장 """
    id = models.AutoField(primary_key=True)  # 명시적으로 id 필드 추가
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following') # 중복 팔로우 방지

    def __str__(self):
        return f"{self.follower} -> {self.following}"

def user_photo_path(instance, filename):
    return f'users/{instance.pk}/photos/{filename}'

class Photo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="photo")
    image = models.ImageField(upload_to=user_photo_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s photo"

