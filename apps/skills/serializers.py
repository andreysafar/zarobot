"""
Skills app serializers
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import SkillCategory, Skill, SkillInstallation, SkillRating


class SkillCategorySerializer(serializers.ModelSerializer):
    """Сериализатор категорий навыков"""
    
    skills_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SkillCategory
        fields = [
            'id', 'name', 'description', 'icon', 'color', 
            'is_active', 'sort_order', 'skills_count'
        ]
    
    def get_skills_count(self, obj):
        return obj.skills.filter(is_public=True, status='active').count()


class SkillCategoryCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания категорий"""
    
    class Meta:
        model = SkillCategory
        fields = ['name', 'description', 'icon', 'color', 'sort_order']


class UserSummarySerializer(serializers.ModelSerializer):
    """Краткая информация о пользователе"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class SkillSerializer(serializers.ModelSerializer):
    """Полный сериализатор навыков"""
    
    creator = UserSummarySerializer(read_only=True)
    category = SkillCategorySerializer(read_only=True)
    popularity_score = serializers.ReadOnlyField()
    installations_count = serializers.SerializerMethodField()
    ratings_count = serializers.SerializerMethodField()
    can_install = serializers.SerializerMethodField()
    
    class Meta:
        model = Skill
        fields = [
            'id', 'name', 'description', 'version', 'creator', 'category',
            'tags', 'price_ia_coins', 'is_free', 'execution_type',
            'handler_module', 'api_endpoint', 'webhook_url', 'langflow_node_id',
            'config_schema', 'requirements', 'capabilities',
            'status', 'is_public', 'total_installations', 'total_revenue',
            'average_rating', 'popularity_score', 'created_at', 'updated_at',
            'published_at', 'installations_count', 'ratings_count', 'can_install'
        ]
    
    def get_installations_count(self, obj):
        return obj.total_installations
    
    def get_ratings_count(self, obj):
        return obj.ratings.count()
    
    def get_can_install(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.can_install(request.user)
        return False


class SkillSummarySerializer(serializers.ModelSerializer):
    """Краткий сериализатор навыков для списков"""
    
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    popularity_score = serializers.ReadOnlyField()
    
    class Meta:
        model = Skill
        fields = [
            'id', 'name', 'description', 'version', 'creator_name',
            'category_name', 'category_icon', 'tags', 'price_ia_coins',
            'is_free', 'total_installations', 'average_rating',
            'popularity_score', 'created_at'
        ]


class SkillCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания навыков"""
    
    class Meta:
        model = Skill
        fields = [
            'name', 'description', 'version', 'category', 'tags',
            'price_ia_coins', 'is_free', 'execution_type',
            'handler_module', 'api_endpoint', 'webhook_url', 'langflow_node_id',
            'config_schema', 'requirements', 'capabilities'
        ]
    
    def create(self, validated_data):
        # Автоматически устанавливаем создателя
        validated_data['creator'] = self.context['request'].user
        validated_data['status'] = 'draft'
        return super().create(validated_data)


class SkillInstallationSerializer(serializers.ModelSerializer):
    """Сериализатор установок навыков"""
    
    skill = SkillSummarySerializer(read_only=True)
    bot_passport_name = serializers.CharField(source='bot_passport.name', read_only=True)
    buyer_name = serializers.CharField(source='buyer.username', read_only=True)
    
    class Meta:
        model = SkillInstallation
        fields = [
            'id', 'skill', 'bot_passport_name', 'buyer_name',
            'price_paid', 'payment_currency', 'status', 'config',
            'is_enabled', 'installed_at', 'updated_at',
            'solana_payment_tx', 'solana_install_tx'
        ]


class SkillInstallationCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания установки навыка"""
    
    skill_id = serializers.UUIDField(write_only=True)
    bot_passport_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = SkillInstallation
        fields = ['skill_id', 'bot_passport_id', 'config']
    
    def create(self, validated_data):
        from apps.bot_core.models import BotPassport
        
        skill_id = validated_data.pop('skill_id')
        bot_passport_id = validated_data.pop('bot_passport_id')
        
        skill = Skill.objects.get(id=skill_id)
        bot_passport = BotPassport.objects.get(id=bot_passport_id)
        
        # Проверка прав доступа
        user = self.context['request'].user
        if bot_passport.owner != user:
            raise serializers.ValidationError("Вы не являетесь владельцем этого бота")
        
        # Проверка возможности установки
        if not skill.can_install(user):
            raise serializers.ValidationError("Навык недоступен для установки")
        
        # Проверка, что навык еще не установлен
        if SkillInstallation.objects.filter(skill=skill, bot_passport=bot_passport).exists():
            raise serializers.ValidationError("Навык уже установлен на этого бота")
        
        validated_data.update({
            'skill': skill,
            'bot_passport': bot_passport,
            'buyer': user,
            'price_paid': skill.price_ia_coins,
            'payment_currency': 'IA_COINS'
        })
        
        return super().create(validated_data)


class SkillRatingSerializer(serializers.ModelSerializer):
    """Сериализатор оценок навыков"""
    
    user_name = serializers.CharField(source='user.username', read_only=True)
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    
    class Meta:
        model = SkillRating
        fields = [
            'id', 'skill_name', 'user_name', 'rating', 'review',
            'created_at', 'updated_at'
        ]


class SkillRatingCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания оценки навыка"""
    
    skill_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = SkillRating
        fields = ['skill_id', 'rating', 'review']
    
    def create(self, validated_data):
        skill_id = validated_data.pop('skill_id')
        skill = Skill.objects.get(id=skill_id)
        user = self.context['request'].user
        
        # Проверка, что пользователь установил этот навык
        if not SkillInstallation.objects.filter(
            skill=skill, buyer=user, status='completed'
        ).exists():
            raise serializers.ValidationError(
                "Вы можете оценивать только установленные навыки"
            )
        
        validated_data.update({
            'skill': skill,
            'user': user
        })
        
        return super().create(validated_data)


class SkillSearchSerializer(serializers.Serializer):
    """Сериализатор для поиска навыков"""
    
    query = serializers.CharField(required=False, allow_blank=True)
    category = serializers.IntegerField(required=False)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    min_rating = serializers.DecimalField(max_digits=3, decimal_places=2, required=False)
    execution_type = serializers.CharField(required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    is_free = serializers.BooleanField(required=False)
    sort_by = serializers.ChoiceField(
        choices=[
            'popularity', 'rating', 'price_asc', 'price_desc',
            'installations', 'created_at', 'name'
        ],
        default='popularity'
    )


class SkillPublishSerializer(serializers.Serializer):
    """Сериализатор для публикации навыка"""
    
    skill_id = serializers.UUIDField()
    solana_private_key = serializers.CharField(write_only=True, required=False)
    
    def validate_skill_id(self, value):
        try:
            skill = Skill.objects.get(id=value)
            if skill.creator != self.context['request'].user:
                raise serializers.ValidationError("Вы не являетесь создателем этого навыка")
            if skill.status not in ['draft', 'rejected']:
                raise serializers.ValidationError("Навык уже опубликован или на модерации")
            return value
        except Skill.DoesNotExist:
            raise serializers.ValidationError("Навык не найден")