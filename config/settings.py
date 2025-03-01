"""
Django settings for config project.

Generated by 'django-admin startproject' using Django 4.2.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path
from datetime import timedelta
from corsheaders.defaults import default_headers
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# 환경 변수에서 OpenAI API 키 가져오기
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
LLM_MODEL = 'gpt-4o-mini'  # 또는 'gpt-4'

SECRET_KEY = os.getenv('SECRET_KEY')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    #third party apps
    'rest_framework_simplejwt', #JWT 인증
    "rest_framework", #DRF
    "corsheaders", #CORS 허용
    
    
    #my apps
    "rag",
    "accounts",
    "llm",  # 새로운 LLM 전용 앱
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware", #CORS 허용
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"


CORS_ALLOW_ALL_ORIGINS = True #TODO: 모든 도메인에서 접근 가능하도록 하는 코드. 배포 후 주석처리
CORS_ALLOW_CREDENTIALS = True #TODO: 쿠키, 인증 토큰 같은 민감한 인증 정보를 포함한 요청을 허용.
CORS_ALLOW_HEADERS = list(default_headers) + [
    "content-type",
]


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  #TODO: JWT 인증 없이 접근 가능. 배포 후 주석처리
        'rest_framework.permissions.IsAuthenticated', #인증 필요한 요청에 대해서 인증 필요 메시지 반환
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication', # 기본 JWT 인증 사용
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),  # 액세스 토큰 유효 기간 1일
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),  # 리프레시 토큰 유효 기간 30일 
    'ROTATE_REFRESH_TOKENS': True,  # 리프레시 토큰 회전 사용, 사용한 리프레시 토큰 블랙리스트 처리
    'BLACKLIST_AFTER_ROTATION': True,  # 회전 후 이전 엑세스 토큰 블랙리스트 처리
    'USER_ID_FIELD': 'user_id',  # 커스텀 User 모델의 ID 필드 이름
    'USER_ID_CLAIM': 'user_id',  # 토큰에 저장될 사용자 ID 클레임 이름
}

# 커스텀 User 모델 설정
AUTH_USER_MODEL = 'accounts.User'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "florence_db",
        "USER": os.getenv("DB_USER", ""),  # 환경 변수에서 가져오거나 기본값 사용
        "PASSWORD": os.getenv("DB_PASSWORD", ""),  # 환경 변수에서 가져오거나 기본값 사용
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "ko-kr"

TIME_ZONE = "Asia/Seoul"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
