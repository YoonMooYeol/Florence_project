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

ALLOWED_HOSTS = ['*']  # 모든 호스트 허용


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
    "rest_framework.authtoken", #Token 인증
    "corsheaders", #CORS 허용
    "drf_spectacular", #API 문서
    
    #my apps
    "rag",
    "accounts",
    "llm",
    "healthcare",
    "calendars",
    
    # allauth 관련
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.kakao',
    'allauth.socialaccount.providers.naver',
    'allauth.socialaccount.providers.google',
    
    # REST API 연동
    'dj_rest_auth',
    'dj_rest_auth.registration',
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
    "allauth.account.middleware.AccountMiddleware", # allauth 미들웨어
]

ROOT_URLCONF = "config.urls"


CORS_ALLOW_ALL_ORIGINS = True #TODO: 모든 도메인에서 접근 가능하도록 하는 코드. 배포 후 주석처리
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    "content-type",
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vue 개발 서버
]


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        # 'rest_framework.permissions.AllowAny',  #TODO: JWT 인증 없이 접근 가능. 배포 후 주석처리
        'rest_framework.permissions.IsAuthenticated', #인증 필요한 요청에 대해서 인증 필요 메시지 반환
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication', # 기본 JWT 인증 사용
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    },
    # 한글 오류 메시지를 위한 예외 처리기 설정
    'EXCEPTION_HANDLER': 'config.exception_handler.custom_exception_handler',
    'NON_FIELD_ERRORS_KEY': 'error',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    'DEFAULT_FILTER_BACKENDS': [ 
        'django_filters.rest_framework.DjangoFilterBackend',
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
        "ENGINE": os.getenv("DB_ENGINE", ""),
        "NAME": os.getenv("DB_NAME", ""),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
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


# SMTP SETTING

import os


EMAIL_SITE = os.getenv("EMAIL_SITE", "Gmail")  # 기본값은 Gmail

# SMTP 설정을 정의
SMTP_CONFIG = {
    "GMAIL": {
        "HOST": "smtp.gmail.com",
        "USE_TLS": True,
        "PORT": 587,
        "HOST_USER": os.getenv('GMAIL_USER', 'your_gmail@gmail.com'),
        "HOST_PASSWORD": os.getenv('GMAIL_PASSWORD', 'your_gmail_password')
    },
    "NAVER": {
        "HOST": "smtp.naver.com",
        "USE_TLS": True,
        "PORT": 587,
        "HOST_USER": os.getenv('NAVER_USER', 'NAVER_EMAIL_USER'),
        "HOST_PASSWORD": os.getenv('NAVER_PASSWORD', 'NAVER_PASSWORD_USER')
    },
    "KAKAO": {
        "HOST": "smtp.kakao.com",
        "USE_TLS": True,
        "PORT": 587,
        "HOST_USER": os.getenv('HOST_USER'),
        "HOST_PASSWORD": os.getenv('HOST_PASSWORD')
    }
}

# 이메일 설정에 맞는 서비스를 선택 (기본값은 Gmail)
EMAIL_CONFIG = SMTP_CONFIG.get(EMAIL_SITE, SMTP_CONFIG['GMAIL'])

# 선택한 이메일 설정 값을 가져오기
HOST = EMAIL_CONFIG['HOST']
USE_TLS = EMAIL_CONFIG['USE_TLS']
PORT = EMAIL_CONFIG['PORT']
HOST_USER = EMAIL_CONFIG['HOST_USER']
HOST_PASSWORD = EMAIL_CONFIG['HOST_PASSWORD']

# Django 설정: 이메일 관련 설정
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = HOST
EMAIL_PORT = PORT
EMAIL_USE_TLS = USE_TLS
EMAIL_HOST_USER = HOST_USER
EMAIL_HOST_PASSWORD = HOST_PASSWORD
DEFAULT_FROM_EMAIL = HOST_USER  # 기본 발신자 이메일 주소

SPECTACULAR_SETTINGS = {
    "COMPONENT_SPLIT_REQUEST": True
}

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Allauth 설정
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = 'optional'  # 개발 중에는 'optional'로 설정
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1

# 최신 allauth 버전 설정
ACCOUNT_LOGIN_METHODS = {'email'} 
ACCOUNT_RATE_LIMITS = {
    'login_failed': {'period': 300, 'limit': 5}  # 5회 실패 시 300초 제한
}

# REST 프레임워크와 JWT 통합
REST_USE_JWT = True
JWT_AUTH_COOKIE = 'jwt-auth'
JWT_AUTH_REFRESH_COOKIE = 'jwt-refresh-token'

# dj-rest-auth 설정
REST_AUTH = {
    'TOKEN_MODEL': None,  # 토큰 모델을 사용하지 않음 (JWT만 사용)
    'JWT_AUTH_COOKIE': 'jwt-auth',
    'JWT_AUTH_REFRESH_COOKIE': 'jwt-refresh-token',
    'USE_JWT': True,
}

# 소셜 어카운트 설정
SOCIALACCOUNT_PROVIDERS = {
    'kakao': {
        'APP': {
            'client_id': os.environ.get('REST_KAKAO_API'),
            'secret': '',  # 카카오는 secret이 없음
            'key': ''
        }
    },
    'naver': {
        'APP': {
            'client_id': os.environ.get('NAVER_CLIENT_ID', ''),
            'secret': os.environ.get('NAVER_CLIENT_SECRET', ''),
            'key': ''
        }
    },
    'google': {
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
            'key': ''
        }
    }
}

# REST Framework 설정 (기존 설정이 있다면 합치기)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'dj_rest_auth.jwt_auth.JWTCookieAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle',
                              'rest_framework.throttling.UserRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'anon': '100/day', 'user': '1000/day'},
    'EXCEPTION_HANDLER': 'config.exception_handler.custom_exception_handler',
}

ACCOUNT_ADAPTER = 'accounts.adapters.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.CustomSocialAccountAdapter'