"""
DRF serializers for Personalities models.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Personality,
    PersonalityCategory,
    PersonalityCategoryMembership,
    PersonalityRating,
    PersonalityTemplate
)


class PersonalityCategorySerializer(serializers.ModelSerializer):
    """Serializer for PersonalityCategory."""
    
    personality_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PersonalityCategory
        fields = [
            'id',
            'name',
            'description',
            'color',
            'icon',
            'personality_count',
            'is_active',
            'sort_order',
            'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_personality_count(self, obj):
        """Get number of active personalities in this category."""
        return obj.personality_memberships.filter(
            personality__is_active=True,
            personality__is_public=True
        ).count()


class PersonalityRatingSerializer(serializers.ModelSerializer):
    """Serializer for PersonalityRating."""
    
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = PersonalityRating
        fields = [
            'id',
            'rating',
            'review',
            'user_username',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'user_username']


class PersonalityRatingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating PersonalityRating."""
    
    class Meta:
        model = PersonalityRating
        fields = ['rating', 'review']
    
    def create(self, validated_data):
        """Create rating with current user and personality from context."""
        validated_data['user'] = self.context['request'].user
        validated_data['personality'] = self.context['personality']
        return super().create(validated_data)


class PersonalitySerializer(serializers.ModelSerializer):
    """Full serializer for Personality with all details."""
    
    creator_username = serializers.CharField(source='creator.username', read_only=True)
    categories = PersonalityCategorySerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()
    can_install = serializers.SerializerMethodField()
    
    class Meta:
        model = Personality
        fields = [
            'id',
            'personality_id',
            'name',
            'description',
            'creator_username',
            'system_prompt',
            'langflow_flow_id',
            'price_ia_coin',
            'is_free',
            'total_installations',
            'total_revenue',
            'popularity_score',
            'categories',
            'average_rating',
            'rating_count',
            'user_rating',
            'can_install',
            'is_active',
            'is_public',
            'is_system',
            'metadata',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'personality_id',
            'creator_username',
            'total_installations',
            'total_revenue',
            'popularity_score',
            'is_free',
            'average_rating',
            'rating_count',
            'user_rating',
            'can_install',
            'created_at',
            'updated_at'
        ]
    
    def get_average_rating(self, obj):
        """Get average rating for this personality."""
        return obj.average_rating
    
    def get_rating_count(self, obj):
        """Get total number of ratings."""
        return obj.ratings.count()
    
    def get_user_rating(self, obj):
        """Get current user's rating for this personality."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                rating = obj.ratings.get(user=request.user)
                return PersonalityRatingSerializer(rating).data
            except PersonalityRating.DoesNotExist:
                pass
        return None
    
    def get_can_install(self, obj):
        """Check if current user can install this personality."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_install(request.user)
        return False


class PersonalitySummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for Personality listings."""
    
    creator_username = serializers.CharField(source='creator.username', read_only=True)
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    primary_category = serializers.SerializerMethodField()
    
    class Meta:
        model = Personality
        fields = [
            'id',
            'personality_id',
            'name',
            'description',
            'creator_username',
            'price_ia_coin',
            'is_free',
            'total_installations',
            'popularity_score',
            'average_rating',
            'rating_count',
            'primary_category',
            'created_at'
        ]
    
    def get_average_rating(self, obj):
        """Get average rating."""
        return obj.average_rating
    
    def get_rating_count(self, obj):
        """Get rating count."""
        return obj.ratings.count()
    
    def get_primary_category(self, obj):
        """Get primary category (first one)."""
        category = obj.categories.first()
        return PersonalityCategorySerializer(category).data if category else None


class PersonalityCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new Personality."""
    
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="List of category IDs to assign to this personality"
    )
    
    class Meta:
        model = Personality
        fields = [
            'name',
            'description',
            'system_prompt',
            'langflow_flow_id',
            'price_ia_coin',
            'is_public',
            'metadata',
            'category_ids'
        ]
    
    def create(self, validated_data):
        """Create personality with current user as creator."""
        category_ids = validated_data.pop('category_ids', [])
        validated_data['creator'] = self.context['request'].user
        
        personality = super().create(validated_data)
        
        # Assign categories
        if category_ids:
            categories = PersonalityCategory.objects.filter(
                id__in=category_ids,
                is_active=True
            )
            for category in categories:
                PersonalityCategoryMembership.objects.create(
                    personality=personality,
                    category=category
                )
        
        return personality


class PersonalityTemplateSerializer(serializers.ModelSerializer):
    """Serializer for PersonalityTemplate."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = PersonalityTemplate
        fields = [
            'id',
            'name',
            'description',
            'category_name',
            'system_prompt_template',
            'metadata_template',
            'usage_count',
            'is_active',
            'created_at'
        ]
        read_only_fields = ['usage_count', 'created_at']


class PersonalityInstallationSerializer(serializers.Serializer):
    """Serializer for personality installation requests."""
    
    bot_passport_id = serializers.CharField(
        help_text="ID of the bot passport to install personality on"
    )
    
    custom_prompt_override = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional custom prompt override"
    )
    
    def validate_bot_passport_id(self, value):
        """Validate that bot passport exists and belongs to user."""
        from apps.bot_core.models import BotPassport
        
        try:
            passport = BotPassport.objects.get(
                passport_id=value,
                owner=self.context['request'].user
            )
            return passport
        except BotPassport.DoesNotExist:
            raise serializers.ValidationError(
                "Bot passport not found or you don't have permission to access it."
            )


class PersonalitySearchSerializer(serializers.Serializer):
    """Serializer for personality search parameters."""
    
    query = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Search query for name/description"
    )
    
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Filter by category IDs"
    )
    
    min_rating = serializers.FloatField(
        required=False,
        min_value=0,
        max_value=5,
        help_text="Minimum average rating"
    )
    
    max_price = serializers.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=0,
        help_text="Maximum price in IA-coin"
    )
    
    is_free = serializers.BooleanField(
        required=False,
        help_text="Filter for free personalities only"
    )
    
    creator_id = serializers.IntegerField(
        required=False,
        help_text="Filter by creator user ID"
    )
    
    sort_by = serializers.ChoiceField(
        choices=[
            'popularity', 'rating', 'price', 'installations', 
            'created_at', 'name'
        ],
        default='popularity',
        help_text="Sort results by field"
    )
    
    sort_order = serializers.ChoiceField(
        choices=['asc', 'desc'],
        default='desc',
        help_text="Sort order"
    )