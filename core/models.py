"""
Core MongoDB models for Zero-Bot platform.
Using MongoEngine for MongoDB integration with data isolation by bot_id.
"""

from mongoengine import Document, EmbeddedDocument, fields
from datetime import datetime
import uuid
from config.tokenomics import ECONOMIC_RULES, NFT_SETTINGS
from django.db import models


class BaseModel(Document):
    """Base model with common fields for all documents."""
    
    created_at = fields.DateTimeField(default=datetime.utcnow)
    updated_at = fields.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'abstract': True,
        'indexes': [
            'created_at',
            'updated_at',
        ]
    }
    
    def save(self, *args, **kwargs):
        """Override save to update updated_at timestamp."""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)


class BotConfig(EmbeddedDocument):
    """Configuration settings for a bot."""
    
    personality = fields.StringField(
        required=True, 
        choices=['iya', 'derValera', 'neJry', 'neJny'],
        default='iya'
    )
    
    # Telegram settings
    telegram_token = fields.StringField(required=True, unique=True)
    telegram_username = fields.StringField(required=True)
    webhook_url = fields.StringField()
    
    # Personality-specific settings
    personality_settings = fields.DictField(default=dict)
    
    # Economic settings
    stars_balance = fields.IntField(default=0, min_value=0)
    iam_balance = fields.IntField(default=0, min_value=0)
    
    # Feature flags
    is_active = fields.BooleanField(default=True)
    is_premium = fields.BooleanField(default=False)
    
    # Usage limits
    daily_message_limit = fields.IntField(default=1000)
    monthly_cost_limit = fields.IntField(default=10000)  # In Stars


class Bot(BaseModel):
    """Main bot document with strict data isolation by bot_id."""
    
    # Unique bot identifier - CRITICAL for data isolation
    bot_id = fields.StringField(
        required=True, 
        unique=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Bot metadata
    name = fields.StringField(required=True, max_length=100)
    description = fields.StringField(max_length=1000)
    
    # Owner information
    owner_id = fields.IntField(required=True)
    owner_wallet_address = fields.StringField(required=True)
    owner_telegram_id = fields.IntField(required=True)
    
    # Bot configuration
    config = fields.EmbeddedDocumentField(BotConfig, required=True)
    
    # NFT information
    nft_token_id = fields.StringField(unique=True, sparse=True)
    nft_metadata = fields.DictField()
    
    # Statistics
    total_messages = fields.IntField(default=0, min_value=0)
    total_users = fields.IntField(default=0, min_value=0)
    total_revenue_stars = fields.IntField(default=0, min_value=0)
    
    # Status
    status = fields.StringField(
        choices=['active', 'suspended', 'deleted'],
        default='active'
    )
    
    meta = {
        'collection': 'bots',
        'indexes': [
            'bot_id',  # Primary index for data isolation
            'owner_id',
            'owner_wallet_address',
            'owner_telegram_id',
            'config.telegram_token',
            'nft_token_id',
            'status',
            ('owner_wallet_address', 'status'),
        ]
    }
    
    def clean(self):
        """Validate bot data according to Zero-Bot rules."""
        # Validate NFT metadata size
        if self.nft_metadata:
            import json
            metadata_size = len(json.dumps(self.nft_metadata).encode('utf-8'))
            max_size = NFT_SETTINGS['METADATA_LIMITS']['max_size_bytes']
            if metadata_size > max_size:
                raise ValueError(f"NFT metadata exceeds {max_size} bytes limit")
        
        # Validate personality
        if self.config and self.config.personality not in ['iya', 'derValera', 'neJry', 'neJny']:
            raise ValueError("Invalid personality type")
    
    def get_data_path(self, user_id: str) -> str:
        """Get the data isolation path for this bot and user."""
        return f"/data/bots/{self.bot_id}/users/{user_id}/"
    
    @classmethod
    def get_by_bot_id(cls, bot_id: str):
        """Get bot by bot_id with error handling."""
        try:
            return cls.objects.get(bot_id=bot_id, status='active')
        except cls.DoesNotExist:
            return None


class UserSession(BaseModel):
    """User session data with strict bot_id isolation."""
    
    # CRITICAL: bot_id comes first for data isolation
    bot_id = fields.StringField(required=True)
    user_id = fields.StringField(required=True)  # Telegram user ID
    
    # Session data
    session_id = fields.StringField(
        required=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # User information
    telegram_username = fields.StringField()
    first_name = fields.StringField()
    last_name = fields.StringField()
    language_code = fields.StringField(default='en')
    
    # Session state
    current_personality = fields.StringField(
        choices=['iya', 'derValera', 'neJry', 'neJny'],
        default='iya'
    )
    conversation_context = fields.DictField(default=dict)
    
    # Usage tracking
    message_count = fields.IntField(default=0, min_value=0)
    stars_spent = fields.IntField(default=0, min_value=0)
    last_message_at = fields.DateTimeField()
    
    # Subscription info
    subscription_type = fields.StringField(
        choices=['free', 'basic', 'premium'],
        default='free'
    )
    subscription_expires_at = fields.DateTimeField()
    
    # Status
    is_active = fields.BooleanField(default=True)
    is_blocked = fields.BooleanField(default=False)
    
    meta = {
        'collection': 'user_sessions',
        'indexes': [
            ('bot_id', 'user_id'),  # Compound index for data isolation
            'bot_id',  # For bot-level queries
            'session_id',
            'last_message_at',
            ('bot_id', 'is_active'),
            ('bot_id', 'subscription_type'),
        ]
    }
    
    def clean(self):
        """Validate user session data."""
        # Ensure bot_id exists
        if not Bot.get_by_bot_id(self.bot_id):
            raise ValueError(f"Bot with bot_id {self.bot_id} does not exist")
    
    def get_data_path(self) -> str:
        """Get the data isolation path for this user session."""
        return f"/data/bots/{self.bot_id}/users/{self.user_id}/"
    
    @classmethod
    def get_or_create_session(cls, bot_id: str, user_id: str, **kwargs):
        """Get existing session or create new one with data isolation."""
        try:
            session = cls.objects.get(bot_id=bot_id, user_id=user_id, is_active=True)
            return session, False
        except cls.DoesNotExist:
            session = cls(bot_id=bot_id, user_id=user_id, **kwargs)
            session.save()
            return session, True


class MessageLog(BaseModel):
    """Message logging with bot_id isolation."""
    
    # CRITICAL: bot_id for data isolation
    bot_id = fields.StringField(required=True)
    user_id = fields.StringField(required=True)
    
    # Message data
    message_id = fields.StringField(required=True)
    message_text = fields.StringField()
    message_type = fields.StringField(
        choices=['text', 'photo', 'document', 'voice', 'video'],
        default='text'
    )
    
    # Processing info
    personality_used = fields.StringField(
        choices=['iya', 'derValera', 'neJry', 'neJny'],
        required=True
    )
    response_text = fields.StringField()
    processing_time_ms = fields.IntField()
    
    # Economic data
    stars_charged = fields.IntField(default=0, min_value=0)
    iam_cost = fields.IntField(default=0, min_value=0)
    
    # Status
    status = fields.StringField(
        choices=['pending', 'processed', 'failed', 'blocked'],
        default='pending'
    )
    error_message = fields.StringField()
    
    meta = {
        'collection': 'message_logs',
        'indexes': [
            ('bot_id', 'user_id', 'created_at'),
            'bot_id',
            'personality_used',
            'status',
            'created_at',
        ]
    }


class PaymentTransaction(BaseModel):
    """Payment transactions with bot_id isolation."""
    
    # CRITICAL: bot_id for data isolation
    bot_id = fields.StringField(required=True)
    user_id = fields.StringField()  # Optional for platform payments
    
    # Transaction data
    transaction_id = fields.StringField(
        required=True, 
        unique=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # Payment details
    currency_type = fields.StringField(
        choices=['stars', 'iam_coins'],
        required=True
    )
    amount = fields.IntField(required=True, min_value=0)
    
    # Transaction type
    transaction_type = fields.StringField(
        choices=[
            'message_payment',
            'subscription_payment', 
            'bot_creation_fee',
            'personality_fee',
            'nft_minting_fee',
            'tool_purchase',
            'payout'
        ],
        required=True
    )
    
    # Parties involved
    from_wallet = fields.StringField()
    to_wallet = fields.StringField()
    
    # Status
    status = fields.StringField(
        choices=['pending', 'completed', 'failed', 'refunded'],
        default='pending'
    )
    
    # Metadata
    description = fields.StringField()
    metadata = fields.DictField(default=dict)
    
    meta = {
        'collection': 'payment_transactions',
        'indexes': [
            'transaction_id',
            ('bot_id', 'status'),
            'currency_type',
            'transaction_type',
            'from_wallet',
            'to_wallet',
            'created_at',
        ]
    }


# Data isolation utility functions
def get_bot_data_path(bot_id: str, user_id: str = None) -> str:
    """Get the standardized data path for bot data isolation."""
    if user_id:
        return f"/data/bots/{bot_id}/users/{user_id}/"
    else:
        return f"/data/bots/{bot_id}/"


def validate_bot_access(bot_id: str, user_wallet: str) -> bool:
    """Validate that user has access to bot data."""
    bot = Bot.get_by_bot_id(bot_id)
    if not bot:
        return False
    return bot.owner_wallet_address == user_wallet


def ensure_data_isolation():
    """Ensure all queries respect bot_id data isolation."""
    # This function can be used as a decorator or middleware
    # to ensure all database queries include bot_id filtering
    pass


class User(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    iam_balance = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.username} ({self.telegram_id})' 