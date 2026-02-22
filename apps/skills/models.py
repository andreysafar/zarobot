"""
Skills app models - Навыки для ботов с Solana registry интеграцией
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from decimal import Decimal
import uuid


class SkillCategory(models.Model):
    """Категории навыков"""
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Название категории навыков"
    )
    description = models.TextField(
        blank=True,
        help_text="Описание категории"
    )
    icon = models.CharField(
        max_length=10,
        blank=True,
        help_text="Emoji иконка категории"
    )
    color = models.CharField(
        max_length=7,
        default='#6366f1',
        help_text="Hex цвет для UI отображения"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Активна ли категория"
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Порядок сортировки"
    )
    
    class Meta:
        db_table = 'skill_categories'
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['sort_order']),
        ]
    
    def __str__(self):
        return f"{self.icon} {self.name}" if self.icon else self.name


class Skill(models.Model):
    """Навык для ботов"""
    
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('pending_review', 'На модерации'),
        ('approved', 'Одобрен'),
        ('rejected', 'Отклонен'),
        ('active', 'Активен'),
        ('deprecated', 'Устарел'),
    ]
    
    EXECUTION_TYPES = [
        ('api_call', 'API вызов'),
        ('code_execution', 'Выполнение кода'),
        ('langflow_node', 'Langflow узел'),
        ('webhook', 'Webhook'),
        ('database_query', 'Запрос к БД'),
    ]
    
    # Basic info
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(
        max_length=200,
        help_text="Название навыка"
    )
    description = models.TextField(
        help_text="Описание навыка"
    )
    version = models.CharField(
        max_length=20,
        default='1.0.0',
        help_text="Версия навыка"
    )
    
    # Creator and ownership
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_skills',
        help_text="Создатель навыка"
    )
    
    # Categories and tags
    category = models.ForeignKey(
        SkillCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='skills',
        help_text="Основная категория навыка"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Теги для поиска"
    )
    
    # Pricing and economics
    price_ia_coins = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Цена в IA-Coins"
    )
    is_free = models.BooleanField(
        default=False,
        help_text="Бесплатный навык"
    )
    revenue_share_creator = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('60.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Процент дохода создателю"
    )
    
    # Technical implementation
    execution_type = models.CharField(
        max_length=50,
        choices=EXECUTION_TYPES,
        default='api_call',
        help_text="Тип выполнения навыка"
    )
    handler_module = models.CharField(
        max_length=200,
        blank=True,
        help_text="Python модуль обработчика"
    )
    api_endpoint = models.URLField(
        blank=True,
        help_text="API endpoint для вызова"
    )
    webhook_url = models.URLField(
        blank=True,
        help_text="Webhook URL"
    )
    langflow_node_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="ID узла в Langflow"
    )
    
    # Configuration and requirements
    config_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON схема конфигурации навыка"
    )
    requirements = models.JSONField(
        default=list,
        blank=True,
        help_text="Требования для установки"
    )
    capabilities = models.JSONField(
        default=list,
        blank=True,
        help_text="Возможности навыка"
    )
    
    # Blockchain integration
    solana_registry_address = models.CharField(
        max_length=44,
        blank=True,
        null=True,
        help_text="Адрес в Solana Skill Registry"
    )
    solana_tx_hash = models.CharField(
        max_length=88,
        blank=True,
        null=True,
        help_text="Hash транзакции регистрации в Solana"
    )
    
    # Status and moderation
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Статус навыка"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Доступен в публичном маркетплейсе"
    )
    moderation_notes = models.TextField(
        blank=True,
        help_text="Заметки модератора"
    )
    
    # Statistics
    total_installations = models.PositiveIntegerField(
        default=0,
        help_text="Общее количество установок"
    )
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Общий доход"
    )
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))],
        help_text="Средняя оценка"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Дата публикации в маркетплейсе"
    )
    
    class Meta:
        db_table = 'skills'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['creator']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
            models.Index(fields=['is_public']),
            models.Index(fields=['price_ia_coins']),
            models.Index(fields=['total_installations']),
            models.Index(fields=['average_rating']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(price_ia_coins__gte=0),
                name='positive_price'
            ),
        ]
    
    def __str__(self):
        return f"{self.name} v{self.version}"
    
    @property
    def popularity_score(self):
        """Расчет популярности навыка (0-10)"""
        # Базовый алгоритм популярности
        installations_score = min(5.0, self.total_installations / 100)
        rating_score = float(self.average_rating)
        revenue_score = min(3.0, float(self.total_revenue) / 1000)
        
        return min(10.0, installations_score + rating_score + revenue_score)
    
    def can_install(self, user):
        """Проверка возможности установки навыка"""
        if not self.is_public or self.status != 'active':
            return False
        
        # TODO: Проверить баланс пользователя
        return True
    
    async def register_on_solana(self, private_key=None):
        """Регистрация навыка в Solana Registry"""
        from blockchain.solana.registry import RegistryClient
        from blockchain.solana.client import SolanaClient
        
        try:
            solana_client = SolanaClient()
            registry_client = RegistryClient(
                solana_client=solana_client,
                registry_program_id="SKILL_REGISTRY_PROGRAM_ID"  # TODO: Real program ID
            )
            
            skill_metadata = {
                "skill_id": str(self.id),
                "name": self.name,
                "description": self.description,
                "version": self.version,
                "category": self.category.name if self.category else "general",
                "tags": self.tags,
                "execution_type": self.execution_type,
                "handler_module": self.handler_module,
                "api_endpoint": self.api_endpoint,
                "config_schema": self.config_schema,
                "requirements": self.requirements,
                "capabilities": self.capabilities,
                "creator_django_id": self.creator.id,
                "created_at": self.created_at.isoformat(),
            }
            
            # TODO: Get creator's Solana address from user profile
            creator_solana_address = "CREATOR_SOLANA_ADDRESS"
            
            result = await registry_client.register_skill(
                creator_address=creator_solana_address,
                skill_metadata=skill_metadata,
                price_ia_coin=self.price_ia_coins,
                private_key=private_key
            )
            
            # Сохранение результата регистрации
            self.solana_registry_address = result.metadata.get("registry_address")
            self.solana_tx_hash = result.tx_hash
            self.status = 'active'
            self.save(update_fields=['solana_registry_address', 'solana_tx_hash', 'status'])
            
            return result
            
        except Exception as e:
            self.status = 'rejected'
            self.moderation_notes = f"Solana registration failed: {e}"
            self.save(update_fields=['status', 'moderation_notes'])
            raise


class SkillInstallation(models.Model):
    """Установка навыка на бота"""
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершена'),
        ('failed', 'Ошибка'),
        ('refunded', 'Возврат'),
    ]
    
    # Relations
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='installations',
        help_text="Установленный навык"
    )
    bot_passport = models.ForeignKey(
        'bot_core.BotPassport',
        on_delete=models.CASCADE,
        related_name='skill_installations',
        help_text="Бот, на который установлен навык"
    )
    buyer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='skill_purchases',
        help_text="Покупатель навыка"
    )
    
    # Payment info
    price_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Цена, уплаченная за навык"
    )
    payment_currency = models.CharField(
        max_length=10,
        default='IA_COINS',
        help_text="Валюта платежа"
    )
    
    # Blockchain transaction info
    solana_payment_tx = models.CharField(
        max_length=88,
        blank=True,
        null=True,
        help_text="Hash транзакции оплаты в Solana"
    )
    solana_install_tx = models.CharField(
        max_length=88,
        blank=True,
        null=True,
        help_text="Hash транзакции установки в Solana"
    )
    
    # Installation details
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Статус установки"
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Конфигурация навыка для данного бота"
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text="Включен ли навык"
    )
    
    # Timestamps
    installed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'skill_installations'
        unique_together = ['skill', 'bot_passport']
        ordering = ['-installed_at']
        indexes = [
            models.Index(fields=['skill']),
            models.Index(fields=['bot_passport']),
            models.Index(fields=['buyer']),
            models.Index(fields=['status']),
            models.Index(fields=['installed_at']),
        ]
    
    def __str__(self):
        return f"{self.skill.name} on {self.bot_passport.name}"
    
    async def process_installation(self):
        """Обработка установки навыка через Solana"""
        from blockchain.solana.registry import RegistryClient
        from blockchain.solana.client import SolanaClient
        
        try:
            self.status = 'processing'
            self.save(update_fields=['status'])
            
            solana_client = SolanaClient()
            registry_client = RegistryClient(
                solana_client=solana_client,
                registry_program_id="SKILL_REGISTRY_PROGRAM_ID"
            )
            
            # TODO: Get buyer's Solana address
            buyer_solana_address = "BUYER_SOLANA_ADDRESS"
            
            result = await registry_client.install_skill(
                bot_nft_address=self.bot_passport.solana_nft_address,
                skill_id=str(self.skill.id),
                buyer_address=buyer_solana_address
            )
            
            # Обновление статуса
            self.status = 'completed'
            self.solana_payment_tx = result.metadata.get("payment_tx")
            self.solana_install_tx = result.tx_hash
            self.save(update_fields=['status', 'solana_payment_tx', 'solana_install_tx'])
            
            # Обновление статистики навыка
            self.skill.total_installations += 1
            self.skill.total_revenue += self.price_paid
            self.skill.save(update_fields=['total_installations', 'total_revenue'])
            
            return result
            
        except Exception as e:
            self.status = 'failed'
            self.save(update_fields=['status'])
            raise


class SkillRating(models.Model):
    """Оценка навыка пользователем"""
    
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='ratings',
        help_text="Оцениваемый навык"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='skill_ratings',
        help_text="Пользователь, оставивший оценку"
    )
    installation = models.ForeignKey(
        SkillInstallation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Связанная установка навыка"
    )
    
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Оценка от 1 до 5"
    )
    review = models.TextField(
        blank=True,
        help_text="Текстовый отзыв"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'skill_ratings'
        unique_together = ['skill', 'user']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['skill']),
            models.Index(fields=['user']),
            models.Index(fields=['rating']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.rating}★ for {self.skill.name}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Пересчет средней оценки навыка
        self.skill.update_average_rating()


# Добавляем метод для обновления средней оценки в модель Skill
def update_average_rating(self):
    """Обновление средней оценки навыка"""
    ratings = self.ratings.all()
    if ratings:
        avg_rating = sum(r.rating for r in ratings) / len(ratings)
        self.average_rating = Decimal(str(round(avg_rating, 2)))
        self.save(update_fields=['average_rating'])

Skill.update_average_rating = update_average_rating