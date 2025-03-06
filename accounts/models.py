from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

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
    name = models.CharField(max_length=100, verbose_name='이름')
    phone_number = models.CharField(
        max_length=15, 
        unique=True,
        verbose_name='전화번호',
        error_messages={
            'unique': "이미 등록된 전화번호입니다.",
            'max_length': "전화번호는 15자를 초과할 수 없습니다.",
            'blank': "전화번호를 입력해주세요.",
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
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
    
    def __str__(self):
        return self.name

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