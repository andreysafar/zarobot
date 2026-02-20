"""
URL configuration for Zero-Bot API.
Implements RESTful routing with data isolation by bot_id.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import (
    UserSessionAPIView, MessageAPIView, PaymentAPIView,
    BotStatsAPIView, health_check, data_isolation_info, validate_economic_rules_endpoint
)

# API v1 URL patterns
urlpatterns = [
    # Health and system endpoints
    path('health/', health_check, name='health_check'),
    path('validate-rules/', validate_economic_rules_endpoint, name='validate_economic_rules'),
    
    # Bot management endpoints (now handled by bot_factory)
    path('api/v1/', include('apps.bot_factory.urls')),

    # Bot-specific endpoints that remain in core
    path('api/v1/bots/<str:bot_id>/stats/', BotStatsAPIView.as_view(), name='bot_stats'),
    
    # User session endpoints (with bot_id isolation)
    path('api/v1/bots/<str:bot_id>/sessions/', UserSessionAPIView.as_view(), name='session_list_create'),
    path('api/v1/bots/<str:bot_id>/sessions/<str:user_id>/', UserSessionAPIView.as_view(), name='session_detail'),
    
    # Message processing endpoints (with bot_id isolation)
    path('api/v1/bots/<str:bot_id>/messages/', MessageAPIView.as_view(), name='message_list_create'),
    path('api/v1/bots/<str:bot_id>/messages/<str:user_id>/', MessageAPIView.as_view(), name='message_user_list'),
    
    # Payment endpoints (with bot_id isolation)
    path('api/v1/payments/', PaymentAPIView.as_view(), name='payment_list_create'),
    path('api/v1/bots/<str:bot_id>/payments/', PaymentAPIView.as_view(), name='bot_payment_list_create'),
    
    # Data isolation information endpoints
    path('api/v1/bots/<str:bot_id>/isolation/', data_isolation_info, name='bot_isolation_info'),
    path('api/v1/bots/<str:bot_id>/isolation/<str:user_id>/', data_isolation_info, name='user_isolation_info'),
    
    # Message router webhooks (include message_router URLs)
    path('', include('apps.message_router.urls')),
]

# Add app name for namespacing
app_name = 'core'

urlpatterns += [path('admin/', admin.site.urls),]
