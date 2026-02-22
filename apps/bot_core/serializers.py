"""
DRF serializers for Bot Core models.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import BotPassport, BotState, PersonalityInstance


class BotPassportSerializer(serializers.ModelSerializer):
    """Serializer for Bot Passport model."""
    
    # Read-only computed fields
    training_progress = serializers.SerializerMethodField()
    marketplace_value_multiplier = serializers.ReadOnlyField()
    can_level_up = serializers.SerializerMethodField()
    
    # Owner information
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    
    class Meta:
        model = BotPassport
        fields = [
            'bot_id',
            'name',
            'description',
            'owner',
            'owner_username',
            'solana_nft_address',
            'ton_nft_address',
            'personality',
            'experience_points',
            'training_level',
            'training_progress',
            'marketplace_value_multiplier',
            'can_level_up',
            'state',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'bot_id',
            'owner',
            'created_at',
            'updated_at',
            'marketplace_value_multiplier',
        ]
    
    def get_training_progress(self, obj):
        """Get training progress percentage."""
        return obj.get_training_progress()
    
    def get_can_level_up(self, obj):
        """Check if bot can level up."""
        return obj.can_level_up()
    
    def validate_name(self, value):
        """Validate bot name."""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Bot name must be at least 2 characters long")
        return value.strip()
    
    def validate_experience_points(self, value):
        """Validate experience points."""
        if value < 0:
            raise serializers.ValidationError("Experience points cannot be negative")
        return value
    
    def validate_training_level(self, value):
        """Validate training level."""
        if not (1 <= value <= 100):
            raise serializers.ValidationError("Training level must be between 1 and 100")
        return value


class BotStateSerializer(serializers.ModelSerializer):
    """Serializer for Bot State model."""
    
    # Bot passport information
    passport_name = serializers.CharField(source='passport.name', read_only=True)
    passport_id = serializers.UUIDField(source='passport.bot_id', read_only=True)
    
    class Meta:
        model = BotState
        fields = [
            'passport',
            'passport_name',
            'passport_id',
            # 'active_prompt',  # To be added when prompts app is created
            'conversation_context',
            'training_data_hash',
            'last_synced_at',
            'sync_status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'passport',
            'last_synced_at',
            'created_at',
            'updated_at',
        ]
    
    def validate_conversation_context(self, value):
        """Validate conversation context size."""
        import json
        if value:
            context_size = len(json.dumps(value).encode('utf-8'))
            if context_size > 512 * 1024:  # 512KB limit
                raise serializers.ValidationError("Conversation context exceeds 512KB limit")
        return value


# SkillInstallationSerializer moved to apps.skills.serializers


class PersonalityInstanceSerializer(serializers.ModelSerializer):
    """Serializer for Personality Instance model."""
    
    # Bot passport information
    passport_name = serializers.CharField(source='passport.name', read_only=True)
    passport_id = serializers.UUIDField(source='passport.bot_id', read_only=True)
    
    # Personality information
    personality_name = serializers.CharField(source='personality.name', read_only=True)
    
    class Meta:
        model = PersonalityInstance
        fields = [
            'id',
            'passport',
            'passport_name',
            'passport_id',
            'personality',
            'personality_name',
            'custom_prompt_override',
            'activated_at',
            'is_active',
        ]
        read_only_fields = [
            'activated_at',
        ]
    
    def validate_custom_prompt_override(self, value):
        """Validate custom prompt override."""
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError("Custom prompt must be at least 10 characters long")
        return value.strip() if value else value


class BotPassportCreateSerializer(serializers.ModelSerializer):
    """Specialized serializer for creating bot passports."""
    
    class Meta:
        model = BotPassport
        fields = [
            'name',
            'description',
            'personality',
        ]
    
    def create(self, validated_data):
        """Create a new bot passport with proper initialization."""
        # Set owner from request user
        validated_data['owner'] = self.context['request'].user
        
        # Initialize with default values
        validated_data['experience_points'] = 0
        validated_data['training_level'] = 1
        validated_data['is_active'] = True
        
        # Create the passport
        passport = super().create(validated_data)
        
        # Create associated bot state
        BotState.objects.create(
            passport=passport,
            conversation_context={},
            sync_status='pending'
        )
        
        return passport


class BotPassportSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for bot passport listings."""
    
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    training_progress = serializers.SerializerMethodField()
    
    class Meta:
        model = BotPassport
        fields = [
            'bot_id',
            'name',
            'owner_username',
            'training_level',
            'experience_points',
            'training_progress',
            'is_active',
            'created_at',
        ]
    
    def get_training_progress(self, obj):
        """Get training progress percentage."""
        return obj.get_training_progress()