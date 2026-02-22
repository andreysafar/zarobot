"""
Dynamic personality system models.

Replaces hardcoded personalities with a flexible, registry-based system
that supports Langflow integration and custom personality creation.
"""

import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal


class Personality(models.Model):
    """
    Personality template loadable from registry.
    
    Represents a personality that can be applied to bots,
    with support for Langflow flows and custom prompts.
    """
    
    # Unique identifiers
    personality_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique personality identifier"
    )
    
    # Basic information
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Personality name (e.g., 'Zero', 'Assistant', 'Creative')"
    )
    
    description = models.TextField(
        help_text="Description of personality traits and behavior"
    )
    
    # Creator and ownership
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_personalities',
        help_text="User who created this personality"
    )
    
    # Prompt system
    system_prompt = models.TextField(
        help_text="Base system prompt that defines personality behavior"
    )
    
    # Langflow integration
    langflow_flow_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Langflow flow ID for dynamic prompt management"
    )
    
    # Economics
    price_ia_coin = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Price in IA-coin to use this personality"
    )
    
    # Status and visibility
    is_active = models.BooleanField(
        default=True,
        help_text="Whether personality is available for use"
    )
    
    is_system = models.BooleanField(
        default=False,
        help_text="Whether this is a system-provided personality"
    )
    
    is_public = models.BooleanField(
        default=True,
        help_text="Whether personality is publicly available"
    )
    
    # Metadata and configuration
    metadata = models.JSONField(
        default=dict,
        help_text="Additional personality metadata (voice, avatar, etc.)"
    )
    
    # Usage statistics
    total_installations = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this personality has been installed"
    )
    
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total revenue generated from this personality"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'personalities'
        ordering = ['-created_at']
        verbose_name_plural = 'Personalities'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['creator']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_public']),
            models.Index(fields=['is_system']),
            models.Index(fields=['price_ia_coin']),
            models.Index(fields=['total_installations']),
        ]
    
    def __str__(self):
        return f"{self.name} by {self.creator.username}"
    
    @property
    def categories(self):
        """Get categories for this personality."""
        return PersonalityCategory.objects.filter(
            personality_memberships__personality=self
        )
    
    @property
    def average_rating(self):
        """Calculate average rating."""
        ratings = self.ratings.all()
        if not ratings:
            return 0
        return sum(r.rating for r in ratings) / len(ratings)
    
    @property
    def popularity_score(self):
        """Calculate popularity score (0-10)."""
        # Simple algorithm: 
        # - Average rating (0-5) * 2 = 0-10 base score
        # - Bonus for installations (log scale)
        # - Bonus for recent activity
        
        base_score = self.average_rating * 2  # Convert 5-star to 10-point scale
        
        # Installation bonus (logarithmic)
        import math
        if self.total_installations > 0:
            install_bonus = min(2.0, math.log10(self.total_installations + 1))
        else:
            install_bonus = 0
        
        # Recent activity bonus
        from django.utils import timezone
        from datetime import timedelta
        
        recent_threshold = timezone.now() - timedelta(days=30)
        if self.updated_at > recent_threshold:
            activity_bonus = 0.5
        else:
            activity_bonus = 0
        
        total_score = base_score + install_bonus + activity_bonus
        return min(10.0, max(0.0, total_score))
    
    def validate(self):
        """Validate personality configuration."""
        try:
            self.clean()
            return True
        except ValidationError:
            return False
    
    def can_install(self, user):
        """Check if user can install this personality."""
        # For now, just return True if validation passes
        # In future, check user balance, permissions, etc.
        return self.validate()
    
    def clean(self):
        """Validate personality data."""
        super().clean()
        
        # Validate system prompt length
        if len(self.system_prompt.strip()) < 10:
            raise ValidationError("System prompt must be at least 10 characters long")
        
        # Validate price
        if self.price_ia_coin < 0:
            raise ValidationError("Price cannot be negative")
        
        # Validate metadata size
        import json
        if self.metadata:
            metadata_size = len(json.dumps(self.metadata).encode('utf-8'))
            if metadata_size > 64 * 1024:  # 64KB limit
                raise ValidationError("Metadata exceeds 64KB limit")
    
    def install_on_bot(self, bot_passport):
        """Install this personality on a bot."""
        from apps.bot_core.models import PersonalityInstance
        
        # Create or update personality instance
        instance, created = PersonalityInstance.objects.get_or_create(
            passport=bot_passport,
            defaults={
                'personality': self,
                'is_active': True
            }
        )
        
        if not created:
            # Update existing instance
            instance.personality = self
            instance.is_active = True
            instance.save()
        
        # Update statistics
        if created:
            self.total_installations += 1
            self.save(update_fields=['total_installations'])
        
        return instance
    
    def get_effective_prompt(self, bot_instance=None):
        """Get the effective prompt for a bot instance."""
        if bot_instance and bot_instance.custom_prompt_override:
            return bot_instance.custom_prompt_override
        return self.system_prompt
    
    @property
    def is_free(self):
        """Check if personality is free to use."""
        return self.price_ia_coin == 0
    
    @property
    def popularity_score(self):
        """Calculate popularity score based on installations."""
        # Simple popularity metric
        return min(self.total_installations / 10, 10.0)


class PersonalityCategory(models.Model):
    """
    Categories for organizing personalities.
    """
    
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Category name (e.g., 'Assistant', 'Creative', 'Technical')"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Category description"
    )
    
    color = models.CharField(
        max_length=7,
        default='#6366f1',
        help_text="Hex color code for UI display"
    )
    
    icon = models.CharField(
        max_length=10,
        blank=True,
        help_text="Emoji or icon for category display"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether category is active"
    )
    
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Sort order for display"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'personality_categories'
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Personality Categories'
    
    def __str__(self):
        return self.name


class PersonalityCategoryMembership(models.Model):
    """
    Many-to-many relationship between personalities and categories.
    """
    
    personality = models.ForeignKey(
        Personality,
        on_delete=models.CASCADE,
        related_name='category_memberships'
    )
    
    category = models.ForeignKey(
        PersonalityCategory,
        on_delete=models.CASCADE,
        related_name='personality_memberships'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'personality_category_memberships'
        unique_together = ['personality', 'category']
        indexes = [
            models.Index(fields=['personality']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.personality.name} in {self.category.name}"


class PersonalityRating(models.Model):
    """
    User ratings for personalities.
    """
    
    personality = models.ForeignKey(
        Personality,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='personality_ratings'
    )
    
    rating = models.PositiveIntegerField(
        help_text="Rating from 1 to 5 stars"
    )
    
    review = models.TextField(
        blank=True,
        help_text="Optional review text"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'personality_ratings'
        unique_together = ['personality', 'user']
        indexes = [
            models.Index(fields=['personality']),
            models.Index(fields=['user']),
            models.Index(fields=['rating']),
            models.Index(fields=['created_at']),
        ]
    
    def clean(self):
        """Validate rating value."""
        super().clean()
        if not (1 <= self.rating <= 5):
            raise ValidationError("Rating must be between 1 and 5")
    
    def __str__(self):
        return f"{self.user.username} rated {self.personality.name}: {self.rating}/5"


class PersonalityTemplate(models.Model):
    """
    Templates for creating new personalities.
    Provides starting points for personality creation.
    """
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Template name"
    )
    
    description = models.TextField(
        help_text="Template description and use cases"
    )
    
    system_prompt_template = models.TextField(
        help_text="System prompt template with placeholders"
    )
    
    metadata_template = models.JSONField(
        default=dict,
        help_text="Default metadata structure"
    )
    
    category = models.ForeignKey(
        PersonalityCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Default category for personalities created from this template"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether template is available for use"
    )
    
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of personalities created from this template"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'personality_templates'
        ordering = ['-usage_count', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['category']),
            models.Index(fields=['usage_count']),
        ]
    
    def __str__(self):
        return f"Template: {self.name}"
    
    def create_personality(self, creator, name, **kwargs):
        """Create a new personality from this template."""
        # Process template placeholders
        system_prompt = self.system_prompt_template.format(**kwargs)
        
        personality = Personality.objects.create(
            name=name,
            description=kwargs.get('description', self.description),
            creator=creator,
            system_prompt=system_prompt,
            metadata=dict(self.metadata_template, **kwargs.get('metadata', {})),
            price_ia_coin=kwargs.get('price_ia_coin', Decimal('0.00'))
        )
        
        # Add to default category if specified
        if self.category:
            PersonalityCategoryMembership.objects.create(
                personality=personality,
                category=self.category
            )
        
        # Update usage count
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
        
        return personality