"""
Core message routing system for Zero-Bot platform.
Handles message routing by bot_id with strict data isolation.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
import json

from core.models import Bot, UserSession, MessageLog
from apps.message_router.personality import PersonalityManager
from config.tokenomics import STARS_ECONOMY, validate_economic_rules

logger = logging.getLogger('zero_bot.message_router')


class MessageRouter:
    """
    Core message routing system with bot_id isolation.
    Routes incoming messages to appropriate personality handlers.
    """
    
    def __init__(self):
        self.personality_manager = PersonalityManager()
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def route_message(self, bot_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route incoming message to appropriate handler with data isolation.
        
        Args:
            bot_id: Unique bot identifier for data isolation
            message_data: Telegram message data
            
        Returns:
            Dict containing response data and processing info
        """
        try:
            # Validate bot exists and is active
            bot = Bot.get_by_bot_id(bot_id)
            if not bot:
                logger.error(f"Bot {bot_id} not found or inactive")
                return self._create_error_response("Bot not found", bot_id)
            
            # Extract user information
            user_id = str(message_data.get('from', {}).get('id', ''))
            if not user_id:
                logger.error(f"No user ID in message for bot {bot_id}")
                return self._create_error_response("Invalid user data", bot_id)
            
            # Get or create user session with data isolation
            session, created = UserSession.get_or_create_session(
                bot_id=bot_id,
                user_id=user_id,
                **self._extract_user_info(message_data)
            )
            
            # Determine personality to use
            personality = self._determine_personality(bot, session, message_data)
            
            # Validate economic rules
            stars_cost = self._calculate_message_cost(personality, message_data)
            if not self._validate_payment(bot, session, stars_cost):
                return self._create_payment_required_response(stars_cost, bot_id)
            
            # Process message with personality
            start_time = datetime.utcnow()
            response = await self.personality_manager.process_message(
                personality=personality,
                message_data=message_data,
                session=session,
                bot_config=bot.config
            )
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Log message with data isolation
            await self._log_message(
                bot_id=bot_id,
                user_id=user_id,
                message_data=message_data,
                response=response,
                personality=personality,
                stars_cost=stars_cost,
                processing_time=processing_time
            )
            
            # Update session
            session.message_count += 1
            session.stars_spent += stars_cost
            session.last_message_at = datetime.utcnow()
            session.current_personality = personality
            session.save()
            
            # Update bot statistics
            bot.total_messages += 1
            bot.total_revenue_stars += stars_cost
            bot.save()
            
            logger.info(f"Message processed for bot {bot_id}, user {user_id}, personality {personality}")
            
            return {
                'success': True,
                'response': response,
                'personality': personality,
                'stars_charged': stars_cost,
                'processing_time_ms': processing_time,
                'bot_id': bot_id,
                'user_id': user_id
            }
            
        except Exception as e:
            logger.error(f"Error routing message for bot {bot_id}: {e}")
            return self._create_error_response(f"Processing error: {str(e)}", bot_id)
    
    def _determine_personality(self, bot: Bot, session: UserSession, message_data: Dict[str, Any]) -> str:
        """
        Determine which personality to use for the message.
        
        Priority:
        1. User's current personality preference
        2. Bot's default personality
        3. Message content analysis
        """
        # Check if user has a personality preference
        if session.current_personality and session.current_personality != bot.config.personality:
            # Validate user can access this personality (premium check, etc.)
            if self._can_use_personality(session, session.current_personality):
                return session.current_personality
        
        # Check for personality switch commands in message
        message_text = message_data.get('text', '').lower()
        personality_commands = {
            '/iya': 'iya',
            '/dervalera': 'derValera', 
            '/nejry': 'neJry',
            '/nejny': 'neJny'
        }
        
        for command, personality in personality_commands.items():
            if message_text.startswith(command):
                if self._can_use_personality(session, personality):
                    return personality
        
        # Use bot's default personality
        return bot.config.personality
    
    def _can_use_personality(self, session: UserSession, personality: str) -> bool:
        """Check if user can access the requested personality."""
        # Basic personalities available to all users
        if personality in ['iya']:
            return True
        
        # Premium personalities require subscription
        if personality in ['derValera', 'neJry', 'neJny']:
            return session.subscription_type in ['basic', 'premium']
        
        return False
    
    def _calculate_message_cost(self, personality: str, message_data: Dict[str, Any]) -> int:
        """Calculate Stars cost for message processing."""
        base_cost = STARS_ECONOMY['USER_PAYMENTS']['message_pricing'].get(personality, 1)
        
        # Additional costs for special message types
        premium_features = STARS_ECONOMY['USER_PAYMENTS']['premium_features']
        if message_data.get('photo'):
            base_cost += premium_features.get('custom_image_generation', 2)
        elif message_data.get('voice'):
            base_cost += 3  # Voice processing cost
        elif message_data.get('document'):
            base_cost += 2  # Document processing cost
        
        return base_cost
    
    def _validate_payment(self, bot: Bot, session: UserSession, cost: int) -> bool:
        """Validate user can pay for message processing."""
        # For now, always allow (payment will be handled by Telegram Stars)
        # In production, check user's Stars balance or subscription
        return True
    
    async def _log_message(self, bot_id: str, user_id: str, message_data: Dict[str, Any], 
                          response: Dict[str, Any], personality: str, stars_cost: int, 
                          processing_time: int):
        """Log message with data isolation."""
        try:
            message_log = MessageLog(
                bot_id=bot_id,
                user_id=user_id,
                message_id=str(message_data.get('message_id', '')),
                message_text=message_data.get('text', ''),
                message_type=self._get_message_type(message_data),
                personality_used=personality,
                response_text=response.get('text', ''),
                processing_time_ms=processing_time,
                stars_charged=stars_cost,
                status='processed'
            )
            message_log.save()
        except Exception as e:
            logger.error(f"Failed to log message for bot {bot_id}: {e}")
    
    def _get_message_type(self, message_data: Dict[str, Any]) -> str:
        """Determine message type from Telegram data."""
        if message_data.get('photo'):
            return 'photo'
        elif message_data.get('voice'):
            return 'voice'
        elif message_data.get('document'):
            return 'document'
        elif message_data.get('video'):
            return 'video'
        else:
            return 'text'
    
    def _extract_user_info(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user information from Telegram message."""
        user_data = message_data.get('from', {})
        return {
            'telegram_username': user_data.get('username', ''),
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
            'language_code': user_data.get('language_code', 'en')
        }
    
    def _create_error_response(self, error_message: str, bot_id: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            'success': False,
            'error': error_message,
            'bot_id': bot_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _create_payment_required_response(self, cost: int, bot_id: str) -> Dict[str, Any]:
        """Create payment required response."""
        return {
            'success': False,
            'error': 'payment_required',
            'stars_required': cost,
            'bot_id': bot_id,
            'message': f'This message requires {cost} Stars to process'
        }
    
    async def get_routing_stats(self, bot_id: str) -> Dict[str, Any]:
        """Get routing statistics for a specific bot."""
        try:
            bot = Bot.get_by_bot_id(bot_id)
            if not bot:
                return {'error': 'Bot not found'}
            
            # Get recent message stats
            recent_messages = MessageLog.objects.filter(
                bot_id=bot_id,
                created_at__gte=datetime.utcnow().replace(hour=0, minute=0, second=0)
            )
            
            personality_stats = {}
            for message in recent_messages:
                personality = message.personality_used
                if personality not in personality_stats:
                    personality_stats[personality] = 0
                personality_stats[personality] += 1
            
            return {
                'bot_id': bot_id,
                'total_messages_today': len(recent_messages),
                'personality_distribution': personality_stats,
                'active_sessions': UserSession.objects.filter(
                    bot_id=bot_id, 
                    is_active=True
                ).count()
            }
        except Exception as e:
            logger.error(f"Error getting routing stats for bot {bot_id}: {e}")
            return {'error': str(e)}


# Global router instance
message_router = MessageRouter() 