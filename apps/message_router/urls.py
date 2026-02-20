"""
URL configuration for message_router app.
Defines webhook endpoints with bot_id isolation.
"""

from django.urls import path
from apps.message_router.webhook_handlers import (
    TelegramWebhookView,
    webhook_health_check,
    set_webhook,
    webhook_stats
)

app_name = 'message_router'

urlpatterns = [
    # Main webhook endpoint for Telegram messages
    # Each bot gets its own webhook URL for data isolation
    path('webhooks/telegram/<str:bot_id>/', 
         TelegramWebhookView.as_view(), 
         name='telegram_webhook'),
    
    # Health check endpoint for webhook verification
    path('webhooks/telegram/<str:bot_id>/health/', 
         webhook_health_check, 
         name='webhook_health'),
    
    # Webhook configuration endpoint
    path('webhooks/telegram/<str:bot_id>/set/', 
         set_webhook, 
         name='set_webhook'),
    
    # Webhook statistics endpoint
    path('webhooks/telegram/<str:bot_id>/stats/', 
         webhook_stats, 
         name='webhook_stats'),
] 