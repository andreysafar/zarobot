"""
URL configuration for Zero-Bot API.
Minimal URLs for dual-chain architecture.
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def health_check(request):
    """Basic health check endpoint."""
    return JsonResponse({'status': 'ok', 'service': 'zero-bot'})

# API v1 URL patterns
urlpatterns = [
    # Health endpoint
    path('health/', health_check, name='health_check'),
    
    # API v1 endpoints
    path('api/v1/', include('apps.bot_core.urls')),
    path('api/v1/', include('apps.personalities.urls')),
    path('api/v1/skills/', include('apps.skills.urls')),
    
    # Admin interface
    path('admin/', admin.site.urls),
]
