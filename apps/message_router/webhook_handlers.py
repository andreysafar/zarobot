"""
Telegram webhook handlers for Zero-Bot platform.
Handles incoming webhooks with bot_id isolation.
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
import asyncio

from core.models import Bot
from apps.message_router.router import message_router
from config.tokenomics import validate_economic_rules

logger = logging.getLogger('zero_bot.webhook')


@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    """
    Handles Telegram webhooks for specific bots with data isolation.
    Each bot has its own webhook endpoint: /webhooks/telegram/{bot_id}
    """
    
    async def post(self, request, bot_id: str):
        """
        Process incoming Telegram webhook for specific bot.
        
        Args:
            request: Django HTTP request
            bot_id: Unique bot identifier for data isolation
        """
        try:
            # Validate bot exists and is active
            bot = Bot.get_by_bot_id(bot_id)
            if not bot:
                logger.warning(f"Webhook received for unknown bot: {bot_id}")
                return JsonResponse({'error': 'Bot not found'}, status=404)
            
            if bot.status != 'active':
                logger.warning(f"Webhook received for inactive bot: {bot_id}")
                return JsonResponse({'error': 'Bot inactive'}, status=403)
            
            # Parse webhook data
            try:
                webhook_data = json.loads(request.body.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in webhook for bot {bot_id}: {e}")
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            
            # Validate webhook structure
            if not self._validate_webhook_data(webhook_data):
                logger.error(f"Invalid webhook structure for bot {bot_id}")
                return JsonResponse({'error': 'Invalid webhook structure'}, status=400)
            
            # Extract message data
            message_data = webhook_data.get('message')
            if not message_data:
                # Handle other update types (callback queries, etc.)
                return await self._handle_non_message_update(bot_id, webhook_data)
            
            # Validate Telegram token (security check)
            if not self._validate_telegram_token(bot, request):
                logger.warning(f"Invalid Telegram token for bot {bot_id}")
                return JsonResponse({'error': 'Unauthorized'}, status=401)
            
            # Log incoming webhook
            logger.info(f"Processing webhook for bot {bot_id}, user {message_data.get('from', {}).get('id')}")
            
            # Route message through message router
            start_time = datetime.utcnow()
            routing_result = await message_router.route_message(bot_id, message_data)
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Handle routing result
            if routing_result.get('success'):
                # Send response back to Telegram
                response_sent = await self._send_telegram_response(
                    bot=bot,
                    chat_id=message_data.get('chat', {}).get('id'),
                    response_data=routing_result.get('response', {})
                )
                
                if response_sent:
                    logger.info(f"Successfully processed webhook for bot {bot_id}, processing time: {processing_time}ms")
                    return JsonResponse({
                        'success': True,
                        'processing_time_ms': processing_time,
                        'personality': routing_result.get('personality'),
                        'stars_charged': routing_result.get('stars_charged', 0)
                    })
                else:
                    logger.error(f"Failed to send response to Telegram for bot {bot_id}")
                    return JsonResponse({'error': 'Failed to send response'}, status=500)
            else:
                # Handle routing errors
                error_message = routing_result.get('error', 'Unknown error')
                logger.error(f"Message routing failed for bot {bot_id}: {error_message}")
                
                # Send error message to user if possible
                if routing_result.get('error') == 'payment_required':
                    await self._send_payment_required_message(
                        bot=bot,
                        chat_id=message_data.get('chat', {}).get('id'),
                        stars_required=routing_result.get('stars_required', 1)
                    )
                
                return JsonResponse({
                    'success': False,
                    'error': error_message,
                    'processing_time_ms': processing_time
                }, status=400)
                
        except Exception as e:
            logger.error(f"Unexpected error processing webhook for bot {bot_id}: {e}")
            return JsonResponse({'error': 'Internal server error'}, status=500)
    
    def _validate_webhook_data(self, webhook_data: Dict[str, Any]) -> bool:
        """Validate basic webhook data structure."""
        required_fields = ['update_id']
        return all(field in webhook_data for field in required_fields)
    
    def _validate_telegram_token(self, bot: Bot, request) -> bool:
        """
        Validate Telegram webhook token for security.
        In production, this should verify the webhook secret token.
        """
        # For now, just check if bot has a valid token
        return bool(bot.config.telegram_token)
    
    async def _handle_non_message_update(self, bot_id: str, webhook_data: Dict[str, Any]) -> JsonResponse:
        """Handle non-message updates (callback queries, inline queries, etc.)."""
        update_type = None
        
        if 'callback_query' in webhook_data:
            update_type = 'callback_query'
            # Handle callback query
            callback_data = webhook_data['callback_query']
            logger.info(f"Callback query for bot {bot_id}: {callback_data.get('data')}")
        
        elif 'inline_query' in webhook_data:
            update_type = 'inline_query'
            # Handle inline query
            inline_data = webhook_data['inline_query']
            logger.info(f"Inline query for bot {bot_id}: {inline_data.get('query')}")
        
        else:
            logger.info(f"Unhandled update type for bot {bot_id}: {list(webhook_data.keys())}")
        
        return JsonResponse({
            'success': True,
            'update_type': update_type,
            'message': 'Update processed'
        })
    
    async def _send_telegram_response(self, bot: Bot, chat_id: int, response_data: Dict[str, Any]) -> bool:
        """
        Send response back to Telegram.
        In production, this would use Telegram Bot API.
        """
        try:
            # For now, just log the response
            # In production, implement actual Telegram API call
            logger.info(f"Sending response to chat {chat_id} for bot {bot.bot_id}: {response_data.get('text', '')}")
            
            # Simulate API call delay
            await asyncio.sleep(0.1)
            
            # TODO: Implement actual Telegram Bot API call
            # response = await telegram_api.send_message(
            #     token=bot.config.telegram_token,
            #     chat_id=chat_id,
            #     text=response_data.get('text', ''),
            #     **response_data.get('options', {})
            # )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending Telegram response for bot {bot.bot_id}: {e}")
            return False
    
    async def _send_payment_required_message(self, bot: Bot, chat_id: int, stars_required: int) -> bool:
        """Send payment required message to user."""
        try:
            payment_message = f"Для обработки этого сообщения требуется {stars_required} ⭐ Stars. Пожалуйста, пополните баланс."
            
            # Log payment required message
            logger.info(f"Payment required for bot {bot.bot_id}, chat {chat_id}: {stars_required} stars")
            
            # TODO: Implement actual Telegram payment message
            # await telegram_api.send_invoice(...)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending payment message for bot {bot.bot_id}: {e}")
            return False


@csrf_exempt
@require_http_methods(["GET"])
def webhook_health_check(request, bot_id: str):
    """
    Health check endpoint for bot webhooks.
    Used by Telegram to verify webhook endpoint.
    """
    try:
        bot = Bot.get_by_bot_id(bot_id)
        if not bot:
            return JsonResponse({'error': 'Bot not found'}, status=404)
        
        return JsonResponse({
            'status': 'healthy',
            'bot_id': bot_id,
            'bot_name': bot.name,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Health check error for bot {bot_id}: {e}")
        return JsonResponse({'error': 'Health check failed'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def set_webhook(request, bot_id: str):
    """
    Set webhook URL for specific bot.
    Used during bot setup to configure Telegram webhook.
    """
    try:
        bot = Bot.get_by_bot_id(bot_id)
        if not bot:
            return JsonResponse({'error': 'Bot not found'}, status=404)
        
        # Parse request data
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        webhook_url = data.get('webhook_url')
        if not webhook_url:
            return JsonResponse({'error': 'webhook_url required'}, status=400)
        
        # TODO: Implement actual Telegram setWebhook API call
        # success = await telegram_api.set_webhook(
        #     token=bot.config.telegram_token,
        #     url=webhook_url
        # )
        
        logger.info(f"Webhook set for bot {bot_id}: {webhook_url}")
        
        return JsonResponse({
            'success': True,
            'bot_id': bot_id,
            'webhook_url': webhook_url,
            'message': 'Webhook configured successfully'
        })
        
    except Exception as e:
        logger.error(f"Error setting webhook for bot {bot_id}: {e}")
        return JsonResponse({'error': 'Failed to set webhook'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def webhook_stats(request, bot_id: str):
    """
    Get webhook statistics for specific bot.
    """
    try:
        # Get routing stats from message router
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        stats = loop.run_until_complete(message_router.get_routing_stats(bot_id))
        loop.close()
        
        return JsonResponse({
            'bot_id': bot_id,
            'webhook_stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting webhook stats for bot {bot_id}: {e}")
        return JsonResponse({'error': 'Failed to get stats'}, status=500) 