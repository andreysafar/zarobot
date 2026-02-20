"""
Django REST Framework serializers for Zero-Bot API.
Handles serialization/deserialization of MongoDB models.
"""

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from core.models import Bot, BotConfig, UserSession, MessageLog, PaymentTransaction
from config.tokenomics import validate_economic_rules, NFT_SETTINGS
import json


class BotConfigSerializer(serializers.Serializer):
    """Serializer for BotConfig embedded document."""
    
    personality = serializers.ChoiceField(
        choices=['iya', 'derValera', 'neJry', 'neJny'],
        default='iya'
    )
    telegram_token = serializers.CharField(max_length=200)
    telegram_username = serializers.CharField(max_length=100)
    webhook_url = serializers.URLField(required=False, allow_blank=True)
    personality_settings = serializers.DictField(default=dict)
    stars_balance = serializers.IntegerField(default=0, min_value=0)
    iam_balance = serializers.IntegerField(default=0, min_value=0)
    is_active = serializers.BooleanField(default=True)
    is_premium = serializers.BooleanField(default=False)
    daily_message_limit = serializers.IntegerField(default=1000, min_value=1)
    monthly_cost_limit = serializers.IntegerField(default=10000, min_value=0)


class BotSerializer(serializers.Serializer):
    """Serializer for Bot model with data isolation validation."""
    
    bot_id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    owner_wallet_address = serializers.CharField(max_length=200)
    owner_telegram_id = serializers.IntegerField()
    config = BotConfigSerializer()
    nft_token_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    nft_metadata = serializers.DictField(required=False, default=dict)
    total_messages = serializers.IntegerField(read_only=True)
    total_users = serializers.IntegerField(read_only=True)
    total_revenue_stars = serializers.IntegerField(read_only=True)
    status = serializers.ChoiceField(
        choices=['active', 'suspended', 'deleted'],
        default='active'
    )
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    def validate_nft_metadata(self, value):
        """Validate NFT metadata size according to Zero-Bot rules."""
        if value:
            metadata_size = len(json.dumps(value).encode('utf-8'))
            max_size = NFT_SETTINGS['METADATA_LIMITS']['max_size_bytes']
            if metadata_size > max_size:
                raise ValidationError(f"NFT metadata exceeds {max_size} bytes limit")
        return value
    
    def validate_config(self, value):
        """Validate bot configuration."""
        # Check if telegram_token is unique (simplified check)
        if 'telegram_token' in value:
            # In real implementation, check against database
            pass
        return value
    
    def create(self, validated_data):
        """Create a new bot with proper configuration."""
        config_data = validated_data.pop('config')
        config = BotConfig(**config_data)
        
        bot = Bot(
            config=config,
            **validated_data
        )
        bot.save()
        return bot
    
    def update(self, instance, validated_data):
        """Update bot with validation."""
        config_data = validated_data.pop('config', None)
        
        if config_data:
            for key, value in config_data.items():
                setattr(instance.config, key, value)
        
        for key, value in validated_data.items():
            setattr(instance, key, value)
        
        instance.save()
        return instance


class UserSessionSerializer(serializers.Serializer):
    """Serializer for UserSession with bot_id isolation."""
    
    bot_id = serializers.CharField(max_length=100)
    user_id = serializers.CharField(max_length=100)
    session_id = serializers.CharField(read_only=True)
    telegram_username = serializers.CharField(max_length=100, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    language_code = serializers.CharField(max_length=10, default='en')
    current_personality = serializers.ChoiceField(
        choices=['iya', 'derValera', 'neJry', 'neJny'],
        default='iya'
    )
    conversation_context = serializers.DictField(default=dict)
    message_count = serializers.IntegerField(read_only=True)
    stars_spent = serializers.IntegerField(read_only=True)
    last_message_at = serializers.DateTimeField(read_only=True)
    subscription_type = serializers.ChoiceField(
        choices=['free', 'basic', 'premium'],
        default='free'
    )
    subscription_expires_at = serializers.DateTimeField(required=False, allow_null=True)
    is_active = serializers.BooleanField(default=True)
    is_blocked = serializers.BooleanField(default=False)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    def validate_bot_id(self, value):
        """Validate that bot_id exists and is active."""
        bot = Bot.get_by_bot_id(value)
        if not bot:
            raise ValidationError(f"Bot with bot_id {value} does not exist or is not active")
        return value
    
    def create(self, validated_data):
        """Create user session with data isolation."""
        session = UserSession(**validated_data)
        session.save()
        return session


class MessageLogSerializer(serializers.Serializer):
    """Serializer for MessageLog with bot_id isolation."""
    
    bot_id = serializers.CharField(max_length=100)
    user_id = serializers.CharField(max_length=100)
    message_id = serializers.CharField(max_length=100)
    message_text = serializers.CharField(required=False, allow_blank=True)
    message_type = serializers.ChoiceField(
        choices=['text', 'photo', 'document', 'voice', 'video'],
        default='text'
    )
    personality_used = serializers.ChoiceField(
        choices=['iya', 'derValera', 'neJry', 'neJny']
    )
    response_text = serializers.CharField(required=False, allow_blank=True)
    processing_time_ms = serializers.IntegerField(required=False, allow_null=True)
    stars_charged = serializers.IntegerField(default=0, min_value=0)
    iam_cost = serializers.IntegerField(default=0, min_value=0)
    status = serializers.ChoiceField(
        choices=['pending', 'processed', 'failed', 'blocked'],
        default='pending'
    )
    error_message = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.DateTimeField(read_only=True)
    
    def validate_bot_id(self, value):
        """Validate that bot_id exists."""
        bot = Bot.get_by_bot_id(value)
        if not bot:
            raise ValidationError(f"Bot with bot_id {value} does not exist")
        return value
    
    def create(self, validated_data):
        """Create message log with data isolation."""
        message_log = MessageLog(**validated_data)
        message_log.save()
        return message_log


class PaymentTransactionSerializer(serializers.Serializer):
    """Serializer for PaymentTransaction with bot_id isolation."""
    
    bot_id = serializers.CharField(max_length=100)
    user_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    transaction_id = serializers.CharField(read_only=True)
    currency_type = serializers.ChoiceField(choices=['stars', 'iam_coins'])
    amount = serializers.IntegerField(min_value=0)
    transaction_type = serializers.ChoiceField(
        choices=[
            'message_payment',
            'subscription_payment',
            'bot_creation_fee',
            'personality_fee',
            'nft_minting_fee',
            'tool_purchase',
            'payout'
        ]
    )
    from_wallet = serializers.CharField(max_length=200, required=False, allow_blank=True)
    to_wallet = serializers.CharField(max_length=200, required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=['pending', 'completed', 'failed', 'refunded'],
        default='pending'
    )
    description = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.DictField(default=dict)
    created_at = serializers.DateTimeField(read_only=True)
    
    def validate_bot_id(self, value):
        """Validate that bot_id exists."""
        bot = Bot.get_by_bot_id(value)
        if not bot:
            raise ValidationError(f"Bot with bot_id {value} does not exist")
        return value
    
    def validate(self, data):
        """Validate transaction according to economic rules."""
        # Validate Stars payments go to bot owner
        if data['currency_type'] == 'stars' and data['transaction_type'] in ['message_payment', 'subscription_payment']:
            bot = Bot.get_by_bot_id(data['bot_id'])
            if bot and data.get('to_wallet') != bot.owner_wallet_address:
                raise ValidationError("Stars payments must go to bot owner")
        
        # Validate IAM payments go to platform
        if data['currency_type'] == 'iam_coins' and data['transaction_type'] in ['bot_creation_fee', 'personality_fee']:
            # Platform wallet validation would go here
            pass
        
        return data
    
    def create(self, validated_data):
        """Create payment transaction with validation."""
        transaction = PaymentTransaction(**validated_data)
        transaction.save()
        return transaction


# Utility serializers for API responses
class BotStatsSerializer(serializers.Serializer):
    """Serializer for bot statistics."""
    
    bot_id = serializers.CharField()
    total_messages = serializers.IntegerField()
    total_users = serializers.IntegerField()
    total_revenue_stars = serializers.IntegerField()
    messages_today = serializers.IntegerField()
    active_users = serializers.IntegerField()
    revenue_this_month = serializers.IntegerField()


class DataIsolationPathSerializer(serializers.Serializer):
    """Serializer for data isolation path information."""
    
    bot_id = serializers.CharField()
    user_id = serializers.CharField(required=False)
    data_path = serializers.CharField()
    isolation_level = serializers.CharField()


class EconomicValidationSerializer(serializers.Serializer):
    """Serializer for economic rule validation."""
    
    rule_name = serializers.CharField()
    is_valid = serializers.BooleanField()
    error_message = serializers.CharField(required=False)
    
    
class APIErrorSerializer(serializers.Serializer):
    """Standardized error response serializer."""
    
    error = serializers.CharField()
    message = serializers.CharField()
    details = serializers.DictField(required=False)
    timestamp = serializers.DateTimeField()
    request_id = serializers.CharField(required=False) 