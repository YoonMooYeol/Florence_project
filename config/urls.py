"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.conf.urls.static import static
from django.conf import settings
from django.http import HttpResponse

def health_check(request):
    return HttpResponse("OK", status=200)

urlpatterns = [
    path('', health_check, name='health-check'),
    path("admin/", admin.site.urls),
    path("v1/accounts/", include("accounts.urls")),
    path("v1/llm/", include("llm.urls")),
    path("v1/calendars/", include("calendars.urls")),
    
    # API 문서
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # dj-rest-auth 엔드포인트
    path('v1/dj-rest-auth/', include('dj_rest_auth.urls')),
    path('v1/dj-rest-auth/registration/', include('dj_rest_auth.registration.urls')),
    
    # 소셜 로그인 URL
    path('v1/accounts/social/', include('allauth.socialaccount.urls')),
    path('health/', health_check, name='health-check'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)