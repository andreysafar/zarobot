"""
Bot Core models for dual-chain architecture.

These models represent the local Django ORM layer that mirrors
and synchronizes with the canonical Solana blockchain state.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import json


class BotPassport(models.Model):
    """
    Bot NFT Passport - canonical identity on Solana blockchain.
    
    This model serves as a local mirror of the Solana NFT passport,
    providing fast queries and caching for the Django application.
    """
    
    # Unique identifiers
    bot_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique bot identifier"
    )
    
    # Ownership
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='bot_passports',
        help_text="Django user who owns this bot"
    )
    
    # Blockchain addresses
    solana_nft_address = models.CharField(
        max_length=64, 
        null=True, 
        blank=True,
        unique=True,
        help_text="Solana NFT mint address (canonical)"
    )
    
    ton_nft_address = models.CharField(
        max_length=64, 
        null=True, 
        blank=True,
        unique=True,
        help_text="TON NFT address (UI wrapper)"
    )
    
    # Bot metadata
    name = models.CharField(
        max_length=100,
        help_text="Bot display name"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Bot description"
    )
    
    # Personality and skills (foreign keys to be added later)
    # personality = models.ForeignKey(
    #     'personalities.Personality',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='bot_instances',
    #     help_text="Active personality"
    # )
    
    # Tamagotchi system
    experience_points = models.PositiveIntegerField(
        default=0,
        help_text="XP earned through training and usage"
    )
    
    training_level = models.PositiveIntegerField(
        default=1,
        help_text="Current training level (1-100)"
    )
    
    # Many-to-many relationships (to be added when skills app is created)
    # skills = models.ManyToManyField('skills.Skill', through='SkillInstallation')
    
    # State mirror (JSON field for PDA state synchronization)
    state = models.JSONField(
        default=dict,
        help_text="Mirror of Solana PDA state"
    )
    
    # Status and metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Whether bot is active and operational"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bot_passports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['owner']),
            models.Index(fields=['solana_nft_address']),
            models.Index(fields=['ton_nft_address']),
            models.Index(fields=['is_active']),
            models.Index(fields=['training_level']),
        ]
    
    def __str__(self):
        return f"{self.name} (Bot {self.bot_id})"
    
    def clean(self):
        """Validate bot passport data."""
        super().clean()
        
        # Validate state JSON size (reasonable limit)
        if self.state:
            state_size = len(json.dumps(self.state).encode('utf-8'))
            if state_size > 1024 * 1024:  # 1MB limit
                raise ValidationError("Bot state exceeds 1MB limit")
    
    def get_training_progress(self):
        """Get training progress to next level."""
        # Simple XP progression: level * 100 XP per level
        current_level_xp = (self.training_level - 1) * 100
        next_level_xp = self.training_level * 100
        progress = (self.experience_points - current_level_xp) / (next_level_xp - current_level_xp)
        return min(max(progress, 0.0), 1.0)
    
    def can_level_up(self):
        """Check if bot has enough XP to level up."""
        required_xp = self.training_level * 100
        return self.experience_points >= required_xp
    
    def level_up(self):
        """Level up the bot if possible."""
        if self.can_level_up() and self.training_level < 100:
            self.training_level += 1
            self.save(update_fields=['training_level'])
            return True
        return False
    
    def add_experience(self, xp_amount):
        """Add experience points and handle level ups."""
        self.experience_points += xp_amount
        
        # Auto level up if possible
        while self.can_level_up() and self.training_level < 100:
            self.level_up()
        
        self.save(update_fields=['experience_points'])
    
    @property
    def marketplace_value_multiplier(self):
        """Calculate value multiplier based on training level."""
        # 10% increase per level (from tokenomics)
        return 1.0 + (self.training_level - 1) * 0.1


class BotState(models.Model):
    """
    Local mirror of Solana PDA state for fast queries.
    
    This model caches the bot's state from the Solana PDA,
    enabling fast reads without blockchain queries.
    """
    
    passport = models.OneToOneField(
        BotPassport,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='local_state'
    )
    
    # Active prompt and conversation
    # active_prompt = models.ForeignKey(
    #     'prompts.Prompt',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     help_text="Currently active prompt template"
    # )
    
    conversation_context = models.JSONField(
        default=dict,
        help_text="Current conversation context and memory"
    )
    
    # Training data
    training_data_hash = models.CharField(
        max_length=64,
        blank=True,
        help_text="Hash of training corpus for integrity"
    )
    
    # Synchronization
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last sync with Solana PDA"
    )
    
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('synced', 'Synced'),
            ('pending', 'Sync Pending'),
            ('conflict', 'Sync Conflict'),
            ('error', 'Sync Error'),
        ],
        default='pending',
        help_text="Synchronization status with blockchain"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'bot_states'
        indexes = [
            models.Index(fields=['sync_status']),
            models.Index(fields=['last_synced_at']),
        ]
    
    def __str__(self):
        return f"State for {self.passport.name}"
    
    def clean(self):
        """Validate bot state data."""
        super().clean()
        
        # Validate conversation context size
        if self.conversation_context:
            context_size = len(json.dumps(self.conversation_context).encode('utf-8'))
            if context_size > 512 * 1024:  # 512KB limit
                raise ValidationError("Conversation context exceeds 512KB limit")
    
    def mark_for_sync(self):
        """Mark state as needing synchronization with blockchain."""
        self.sync_status = 'pending'
        self.save(update_fields=['sync_status', 'updated_at'])
    
    def mark_synced(self):
        """Mark state as successfully synchronized."""
        from django.utils import timezone
        self.sync_status = 'synced'
        self.last_synced_at = timezone.now()
        self.save(update_fields=['sync_status', 'last_synced_at', 'updated_at'])
    
    def mark_sync_error(self):
        """Mark state synchronization as failed."""
        self.sync_status = 'error'
        self.save(update_fields=['sync_status', 'updated_at'])


# Placeholder models for relationships (will be properly implemented when other apps are created)

class SkillInstallation(models.Model):
    """
    Through model for bot-skill relationships.
    Tracks which skills are installed on which bots.
    """
    
    passport = models.ForeignKey(
        BotPassport,
        on_delete=models.CASCADE,
        related_name='skill_installations'
    )
    
    # skill = models.ForeignKey('skills.Skill', on_delete=models.CASCADE)  # To be added later
    
    installed_at = models.DateTimeField(auto_now_add=True)
    
    config = models.JSONField(
        default=dict,
        help_text="Skill-specific configuration"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether skill is currently active"
    )
    
    class Meta:
        db_table = 'skill_installations'
        # unique_together = ['passport', 'skill']  # To be added later
        indexes = [
            models.Index(fields=['passport']),
            models.Index(fields=['installed_at']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"Skill installation for {self.passport.name}"


class PersonalityInstance(models.Model):
    """
    Personality bound to a specific bot.
    Allows customization of personality prompts per bot.
    """
    
    passport = models.ForeignKey(
        BotPassport,
        on_delete=models.CASCADE,
        related_name='personality_instances'
    )
    
    # personality = models.ForeignKey('personalities.Personality', on_delete=models.CASCADE)  # To be added later
    
    custom_prompt_override = models.TextField(
        blank=True,
        help_text="Custom prompt override for this bot instance"
    )
    
    activated_at = models.DateTimeField(auto_now_add=True)
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this personality instance is active"
    )
    
    class Meta:
        db_table = 'personality_instances'
        indexes = [
            models.Index(fields=['passport']),
            models.Index(fields=['activated_at']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"Personality instance for {self.passport.name}"