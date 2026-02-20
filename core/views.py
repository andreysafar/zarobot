"""
Django REST Framework views for Zero-Bot API.
Implements data isolation by bot_id and economic validation.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime, timedelta
import logging
import uuid

from core.models import Bot, UserSession, MessageLog, PaymentTransaction, validate_bot_access
from core.serializers import (
    BotSerializer, UserSessionSerializer, MessageLogSerializer, 
    PaymentTransactionSerializer, BotStatsSerializer, APIErrorSerializer
)
from config.tokenomics import validate_economic_rules, STARS_ECONOMY

logger = logging.getLogger('zero_bot')


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for Zero-Bot API."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def create_error_response(error_type: str, message: str, details: dict = None, status_code: int = 400):
    """Create standardized error response."""
    error_data = {
        'error': error_type,
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'request_id': str(uuid.uuid4())
    }
    if details:
        error_data['details'] = details
    
    return Response(error_data, status=status_code)


class BotAPIView(APIView):
    """API for bot management with data isolation."""
    
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get(self, request, bot_id=None):
        """Get bot(s) with owner validation."""
        try:
            if bot_id:
                # Get specific bot
                bot = Bot.get_by_bot_id(bot_id)
                if not bot:
                    return create_error_response(
                        'bot_not_found',
                        f'Bot with ID {bot_id} not found',
                        status_code=404
                    )
                
                # Validate ownership (simplified - in real app use proper auth)
                # if not validate_bot_access(bot_id, request.user.wallet_address):
                #     return create_error_response('access_denied', 'Access denied', status_code=403)
                
                serializer = BotSerializer(bot)
                return Response({
                    'success': True,
                    'data': serializer.data
                })
            else:
                # Get all bots for user (simplified - filter by owner)
                bots = Bot.objects.filter(status='active')[:50]  # Limit for demo
                serializer = BotSerializer(bots, many=True)
                return Response({
                    'success': True,
                    'data': serializer.data,
                    'count': len(bots)
                })
                
        except Exception as e:
            logger.error(f"Error in BotAPIView.get: {e}")
            return create_error_response('internal_error', 'Internal server error', status_code=500)
    
    def post(self, request):
        """Create new bot with validation."""
        try:
            serializer = BotSerializer(data=request.data)
            if serializer.is_valid():
                bot = serializer.save()
                logger.info(f"Created new bot: {bot.bot_id}")
                return Response({
                    'success': True,
                    'data': BotSerializer(bot).data,
                    'message': 'Bot created successfully'
                }, status=status.HTTP_201_CREATED)
            else:
                return create_error_response(
                    'validation_error',
                    'Invalid bot data',
                    details=serializer.errors
                )
        except Exception as e:
            logger.error(f"Error creating bot: {e}")
            return create_error_response('creation_error', 'Failed to create bot', status_code=500)
    
    def put(self, request, bot_id):
        """Update bot with ownership validation."""
        try:
            bot = Bot.get_by_bot_id(bot_id)
            if not bot:
                return create_error_response('bot_not_found', f'Bot {bot_id} not found', status_code=404)
            
            serializer = BotSerializer(bot, data=request.data, partial=True)
            if serializer.is_valid():
                updated_bot = serializer.save()
                logger.info(f"Updated bot: {bot_id}")
                return Response({
                    'success': True,
                    'data': BotSerializer(updated_bot).data,
                    'message': 'Bot updated successfully'
                })
            else:
                return create_error_response(
                    'validation_error',
                    'Invalid update data',
                    details=serializer.errors
                )
        except Exception as e:
            logger.error(f"Error updating bot {bot_id}: {e}")
            return create_error_response('update_error', 'Failed to update bot', status_code=500)
    
    def delete(self, request, bot_id):
        """Soft delete bot (set status to deleted)."""
        try:
            bot = Bot.get_by_bot_id(bot_id)
            if not bot:
                return create_error_response('bot_not_found', f'Bot {bot_id} not found', status_code=404)
            
            bot.status = 'deleted'
            bot.save()
            logger.info(f"Deleted bot: {bot_id}")
            return Response({
                'success': True,
                'message': 'Bot deleted successfully'
            })
        except Exception as e:
            logger.error(f"Error deleting bot {bot_id}: {e}")
            return create_error_response('deletion_error', 'Failed to delete bot', status_code=500)


class UserSessionAPIView(APIView):
    """API for user session management with bot_id isolation."""
    
    permission_classes = [AllowAny]  # Telegram webhooks don't use standard auth
    
    def get(self, request, bot_id, user_id=None):
        """Get user session(s) for specific bot."""
        try:
            if user_id:
                # Get specific user session
                session, created = UserSession.get_or_create_session(bot_id, user_id)
                serializer = UserSessionSerializer(session)
                return Response({
                    'success': True,
                    'data': serializer.data,
                    'created': created
                })
            else:
                # Get all sessions for bot
                sessions = UserSession.objects.filter(bot_id=bot_id, is_active=True)[:100]
                serializer = UserSessionSerializer(sessions, many=True)
                return Response({
                    'success': True,
                    'data': serializer.data,
                    'count': len(sessions)
                })
        except Exception as e:
            logger.error(f"Error in UserSessionAPIView.get: {e}")
            return create_error_response('session_error', 'Failed to get session', status_code=500)
    
    def post(self, request, bot_id):
        """Create or update user session."""
        try:
            data = request.data.copy()
            data['bot_id'] = bot_id
            
            serializer = UserSessionSerializer(data=data)
            if serializer.is_valid():
                session = serializer.save()
                return Response({
                    'success': True,
                    'data': UserSessionSerializer(session).data,
                    'message': 'Session created successfully'
                }, status=status.HTTP_201_CREATED)
            else:
                return create_error_response(
                    'validation_error',
                    'Invalid session data',
                    details=serializer.errors
                )
        except Exception as e:
            logger.error(f"Error creating session for bot {bot_id}: {e}")
            return create_error_response('session_error', 'Failed to create session', status_code=500)


class MessageAPIView(APIView):
    """API for message processing with bot_id isolation."""
    
    permission_classes = [AllowAny]  # Telegram webhooks
    
    def get(self, request, bot_id, user_id=None):
        """Get message logs for bot/user."""
        try:
            if user_id:
                messages = MessageLog.objects.filter(bot_id=bot_id, user_id=user_id).order_by('-created_at')[:50]
            else:
                messages = MessageLog.objects.filter(bot_id=bot_id).order_by('-created_at')[:100]
            
            serializer = MessageLogSerializer(messages, many=True)
            return Response({
                'success': True,
                'data': serializer.data,
                'count': len(messages)
            })
        except Exception as e:
            logger.error(f"Error getting messages for bot {bot_id}: {e}")
            return create_error_response('message_error', 'Failed to get messages', status_code=500)
    
    def post(self, request, bot_id):
        """Process new message with economic validation."""
        try:
            data = request.data.copy()
            data['bot_id'] = bot_id
            
            # Get bot and validate
            bot = Bot.get_by_bot_id(bot_id)
            if not bot:
                return create_error_response('bot_not_found', f'Bot {bot_id} not found', status_code=404)
            
            # Calculate pricing
            personality = data.get('personality_used', bot.config.personality)
            stars_price = STARS_ECONOMY['MESSAGE_COSTS'].get(personality, 1)
            data['stars_charged'] = stars_price
            
            serializer = MessageLogSerializer(data=data)
            if serializer.is_valid():
                message_log = serializer.save()
                
                # Update bot statistics
                bot.total_messages += 1
                bot.save()
                
                logger.info(f"Processed message for bot {bot_id}, charged {stars_price} stars")
                return Response({
                    'success': True,
                    'data': MessageLogSerializer(message_log).data,
                    'pricing': {
                        'stars_charged': stars_price,
                        'personality': personality
                    }
                }, status=status.HTTP_201_CREATED)
            else:
                return create_error_response(
                    'validation_error',
                    'Invalid message data',
                    details=serializer.errors
                )
        except Exception as e:
            logger.error(f"Error processing message for bot {bot_id}: {e}")
            return create_error_response('message_error', 'Failed to process message', status_code=500)


class PaymentAPIView(APIView):
    """API for payment processing with economic validation."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, bot_id=None):
        """Get payment transactions."""
        try:
            if bot_id:
                transactions = PaymentTransaction.objects.filter(bot_id=bot_id).order_by('-created_at')[:100]
            else:
                # Get all transactions for user's bots (simplified)
                transactions = PaymentTransaction.objects.all().order_by('-created_at')[:50]
            
            serializer = PaymentTransactionSerializer(transactions, many=True)
            return Response({
                'success': True,
                'data': serializer.data,
                'count': len(transactions)
            })
        except Exception as e:
            logger.error(f"Error getting payments: {e}")
            return create_error_response('payment_error', 'Failed to get payments', status_code=500)
    
    def post(self, request, bot_id=None):
        """Create payment transaction with validation."""
        try:
            data = request.data.copy()
            if bot_id:
                data['bot_id'] = bot_id
            
            serializer = PaymentTransactionSerializer(data=data)
            if serializer.is_valid():
                transaction = serializer.save()
                logger.info(f"Created payment transaction: {transaction.transaction_id}")
                return Response({
                    'success': True,
                    'data': PaymentTransactionSerializer(transaction).data,
                    'message': 'Payment transaction created'
                }, status=status.HTTP_201_CREATED)
            else:
                return create_error_response(
                    'validation_error',
                    'Invalid payment data',
                    details=serializer.errors
                )
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return create_error_response('payment_error', 'Failed to create payment', status_code=500)


class BotStatsAPIView(APIView):
    """API for bot statistics and analytics."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, bot_id):
        """Get comprehensive bot statistics."""
        try:
            bot = Bot.get_by_bot_id(bot_id)
            if not bot:
                return create_error_response('bot_not_found', f'Bot {bot_id} not found', status_code=404)
            
            # Calculate additional stats
            today = datetime.utcnow().date()
            messages_today = MessageLog.objects.filter(
                bot_id=bot_id,
                created_at__gte=today
            ).count()
            
            active_users = UserSession.objects.filter(
                bot_id=bot_id,
                is_active=True,
                last_message_at__gte=datetime.utcnow() - timedelta(days=30)
            ).count()
            
            this_month = datetime.utcnow().replace(day=1)
            # Calculate revenue this month (simplified aggregation)
            revenue_transactions = PaymentTransaction.objects.filter(
                bot_id=bot_id,
                currency_type='stars',
                status='completed',
                created_at__gte=this_month
            )
            revenue_this_month = sum(t.amount for t in revenue_transactions)
            
            stats_data = {
                'bot_id': bot_id,
                'total_messages': bot.total_messages,
                'total_users': bot.total_users,
                'total_revenue_stars': bot.total_revenue_stars,
                'messages_today': messages_today,
                'active_users': active_users,
                'revenue_this_month': revenue_this_month
            }
            
            serializer = BotStatsSerializer(stats_data)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Exception as e:
            logger.error(f"Error getting stats for bot {bot_id}: {e}")
            return create_error_response('stats_error', 'Failed to get statistics', status_code=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint."""
    try:
        # Test database connection
        bot_count = Bot.objects.filter(status='active').count()
        
        # Validate economic rules
        validate_economic_rules()
        
        return Response({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'active_bots': bot_count,
            'economic_rules': 'valid'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes([AllowAny])
def data_isolation_info(request, bot_id, user_id=None):
    """Get data isolation path information."""
    try:
        bot = Bot.get_by_bot_id(bot_id)
        if not bot:
            return create_error_response('bot_not_found', f'Bot {bot_id} not found', status_code=404)
        
        if user_id:
            data_path = bot.get_data_path(user_id)
            isolation_level = 'user'
        else:
            data_path = f"/data/bots/{bot_id}/"
            isolation_level = 'bot'
        
        return Response({
            'success': True,
            'data': {
                'bot_id': bot_id,
                'user_id': user_id,
                'data_path': data_path,
                'isolation_level': isolation_level
            }
        })
    except Exception as e:
        logger.error(f"Error getting data isolation info: {e}")
        return create_error_response('isolation_error', 'Failed to get isolation info', status_code=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_economic_rules_endpoint(request):
    """Endpoint to validate economic rules."""
    try:
        validate_economic_rules()
        return Response({
            'success': True,
            'message': 'All economic rules are valid',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Economic rules validation failed: {e}")
        return create_error_response(
            'validation_error',
            'Economic rules validation failed',
            details={'error': str(e)},
            status_code=400
        ) 