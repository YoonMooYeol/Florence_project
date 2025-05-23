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
django_env = os.environ.get('DJANGO_ENV')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['*']
# 만약 www.nooridal.com도 사용한다면:
# ALLOWED_HOSTS = ['nooridal.com', 'www.nooridal.com']


# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    #third party apps
    'sorl.thumbnail',  # 썸네일 라이브러리
    'rest_framework_simplejwt', #JWT 인증
    "rest_framework", #DRF
    "rest_framework.authtoken", #Token 인증
    'rest_framework_simplejwt.token_blacklist', # 토큰 블랙리스트 기능
    "corsheaders", #CORS 허용
    "drf_spectacular", #API 문서
    'django_celery_beat', # Celery
    
    #my apps
    "accounts",
    "llm",
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
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False

# HSTS 설정 (1년 동안 HTTPS만 허용, 서브도메인 포함, 프리로드 신청)
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    "content-type",
]

# 허용할 오리진 확장 (이미 설정된 것 외에도)
CORS_ALLOWED_ORIGINS = [
    "https://nooridal.com",
    "https://www.nooridal.com",
    "http://localhost:3000",  # React 개발 서버
    "http://localhost:8000",  # Django 개발 서버
    "https://nooridal.click",  # 카카오 콜백 URL
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



if django_env == 'development':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('MY_DB_NAME'),
            'USER': os.getenv('MY_DB_USER'),
            'PASSWORD': os.getenv('MY_DB_PASSWORD'),
            'HOST': os.getenv('MY_DB_HOST'),
            'PORT': os.getenv('MY_DB_PORT'),
            'CONN_MAX_AGE': 600
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT'),
            'CONN_MAX_AGE': 600
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


EMAIL_SITE = os.getenv("EMAIL_SERVICE")  # 기본값은 Gmail

# SMTP 설정을 정의
SMTP_CONFIG = {
    "GMAIL": {
        "HOST": "smtp.gmail.com",
        "USE_TLS": True,
        "PORT": 587,
        "HOST_USER": os.getenv('GMAIL_USER'),
        "HOST_PASSWORD": os.getenv('GMAIL_PASSWORD')
    },
    "NAVER": {
        "HOST": "smtp.naver.com",
        "USE_TLS": True,
        "PORT": 587,
        "HOST_USER": os.getenv('NAVER_USER'),
        "HOST_PASSWORD": os.getenv('NAVER_PASSWORD')
    },
    "KAKAO": {
        "HOST": "smtp.kakao.com",
        "USE_TLS": True,
        "PORT": 587,
        "HOST_USER": os.getenv('KAKAO_USER'),
        "HOST_PASSWORD": os.getenv('KAKAO_PASSWORD')
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

# Celery 설정

if django_env == 'development':
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
else:
    CELERY_BROKER_URL = 'redis://redis:6379/0'
    CELERY_RESULT_BACKEND = 'redis://redis:6379/0'

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE  # 한국 시간대 설정
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Celery Beat 설정
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'summarize-yesterday-conversations': {
        'task': 'calendars.tasks.auto_summarize_yesterday_conversations',
        'schedule': crontab(hour=3, minute=0),  # 매일 새벽 3시에 실행
        # 'schedule': 10.0,  # 10초마다 실행 (테스트용)
    },
    # 임신 주차 자동 업데이트
    'update-pregnancy-weeks': {
        'task': 'accounts.tasks.update_pregnancy_weeks',
        'schedule': crontab(hour=0, minute=0),  # 매일 자정 0시 0분 실행
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
        "TIMEOUT": 600,
    }
}

# Media
BASE_DIR = Path(__file__).resolve().parent.parent

# 이미지 파일 저장 경로
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 정적 파일 저장 경로
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

