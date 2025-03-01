from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid

class UserManager(BaseUserManager):
    """커스텀 User 모델 매니저"""
    
    def create_user(self, email, name, password=None, **extra_fields):
        """일반 사용자 생성"""
        if not email:
            raise ValueError('이메일은 필수입니다')
        
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, name, password=None, **extra_fields):
        """관리자 사용자 생성"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        return self.create_user(email, name, password, **extra_fields)

class User(AbstractUser):
    """커스텀 User 모델"""
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], blank=True, null=True)
    is_pregnant = models.BooleanField(default=False)
    address = models.CharField(max_length=255, blank=True, null=True)
    # AbstractUser에서 상속받은 필드 중 사용하지 않을 필드 비활성화
    username = None  # username 필드 사용 안 함
    
    # 이메일을 사용자 식별자로 사용
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    objects = UserManager()
    
    def __str__(self):
        return self.name