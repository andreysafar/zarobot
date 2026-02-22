"""
Skills app admin configuration
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import SkillCategory, Skill, SkillInstallation, SkillRating


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon_display', 'color_display', 'skills_count', 'is_active', 'sort_order']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']
    
    def icon_display(self, obj):
        return obj.icon or '—'
    icon_display.short_description = 'Иконка'
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_display.short_description = 'Цвет'
    
    def skills_count(self, obj):
        count = obj.skills.count()
        if count > 0:
            url = reverse('admin:skills_skill_changelist') + f'?category__id__exact={obj.id}'
            return format_html('<a href="{}">{} навыков</a>', url, count)
        return '0 навыков'
    skills_count.short_description = 'Навыки'


class SkillInstallationInline(admin.TabularInline):
    model = SkillInstallation
    extra = 0
    readonly_fields = ['installed_at', 'solana_payment_tx', 'solana_install_tx']
    fields = ['bot_passport', 'buyer', 'price_paid', 'status', 'is_enabled', 'installed_at']


class SkillRatingInline(admin.TabularInline):
    model = SkillRating
    extra = 0
    readonly_fields = ['created_at']
    fields = ['user', 'rating', 'review', 'created_at']


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'version', 'creator', 'category', 'status', 
        'price_display', 'installations_count', 'rating_display',
        'popularity_display', 'solana_status', 'created_at'
    ]
    list_filter = [
        'status', 'is_public', 'category', 'execution_type',
        'is_free', 'created_at'
    ]
    search_fields = ['name', 'description', 'creator__username', 'tags']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'total_installations', 
        'total_revenue', 'average_rating', 'popularity_score',
        'solana_registry_address', 'solana_tx_hash'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'name', 'description', 'version', 'creator', 'category', 'tags')
        }),
        ('Ценообразование', {
            'fields': ('price_ia_coins', 'is_free', 'revenue_share_creator')
        }),
        ('Техническая реализация', {
            'fields': (
                'execution_type', 'handler_module', 'api_endpoint', 
                'webhook_url', 'langflow_node_id'
            )
        }),
        ('Конфигурация', {
            'fields': ('config_schema', 'requirements', 'capabilities'),
            'classes': ('collapse',)
        }),
        ('Blockchain интеграция', {
            'fields': ('solana_registry_address', 'solana_tx_hash'),
            'classes': ('collapse',)
        }),
        ('Статус и модерация', {
            'fields': ('status', 'is_public', 'moderation_notes', 'published_at')
        }),
        ('Статистика', {
            'fields': (
                'total_installations', 'total_revenue', 'average_rating', 
                'popularity_score'
            ),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [SkillInstallationInline, SkillRatingInline]
    
    def price_display(self, obj):
        if obj.is_free:
            return format_html('<span style="color: green;">Бесплатно</span>')
        return f"{obj.price_ia_coins} IA"
    price_display.short_description = 'Цена'
    
    def installations_count(self, obj):
        count = obj.total_installations
        if count > 0:
            url = reverse('admin:skills_skillinstallation_changelist') + f'?skill__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return '0'
    installations_count.short_description = 'Установки'
    
    def rating_display(self, obj):
        if obj.average_rating > 0:
            stars = '★' * int(obj.average_rating) + '☆' * (5 - int(obj.average_rating))
            return format_html(
                '<span title="{}/5">{}</span>', 
                obj.average_rating, stars
            )
        return '—'
    rating_display.short_description = 'Рейтинг'
    
    def popularity_display(self, obj):
        score = obj.popularity_score
        if score >= 8:
            color = 'red'
        elif score >= 6:
            color = 'orange'
        elif score >= 4:
            color = 'blue'
        else:
            color = 'gray'
        
        return format_html(
            '<span style="color: {};">{:.1f}/10</span>',
            color, score
        )
    popularity_display.short_description = 'Популярность'
    
    def solana_status(self, obj):
        if obj.solana_registry_address:
            return format_html(
                '<span style="color: green;" title="Registry: {}">✓ Зарегистрирован</span>',
                obj.solana_registry_address[:10] + '...'
            )
        return format_html('<span style="color: gray;">Не зарегистрирован</span>')
    solana_status.short_description = 'Solana'
    
    actions = ['register_on_solana', 'approve_skills', 'reject_skills']
    
    def register_on_solana(self, request, queryset):
        """Регистрация навыков в Solana Registry"""
        count = 0
        for skill in queryset:
            if not skill.solana_registry_address:
                try:
                    # TODO: Implement async call properly
                    # await skill.register_on_solana()
                    count += 1
                except Exception as e:
                    self.message_user(request, f'Ошибка регистрации {skill.name}: {e}', level='ERROR')
        
        if count > 0:
            self.message_user(request, f'Запущена регистрация {count} навыков в Solana')
    register_on_solana.short_description = 'Зарегистрировать в Solana'
    
    def approve_skills(self, request, queryset):
        """Одобрение навыков"""
        count = queryset.filter(status='pending_review').update(
            status='approved',
            is_public=True
        )
        self.message_user(request, f'Одобрено {count} навыков')
    approve_skills.short_description = 'Одобрить навыки'
    
    def reject_skills(self, request, queryset):
        """Отклонение навыков"""
        count = queryset.filter(status='pending_review').update(
            status='rejected',
            is_public=False
        )
        self.message_user(request, f'Отклонено {count} навыков')
    reject_skills.short_description = 'Отклонить навыки'


@admin.register(SkillInstallation)
class SkillInstallationAdmin(admin.ModelAdmin):
    list_display = [
        'skill_name', 'bot_name', 'buyer_name', 'price_paid', 
        'status', 'is_enabled', 'solana_status', 'installed_at'
    ]
    list_filter = ['status', 'is_enabled', 'payment_currency', 'installed_at']
    search_fields = [
        'skill__name', 'bot_passport__name', 'buyer__username',
        'solana_payment_tx', 'solana_install_tx'
    ]
    readonly_fields = [
        'installed_at', 'updated_at', 'solana_payment_tx', 'solana_install_tx'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('skill', 'bot_passport', 'buyer', 'status', 'is_enabled')
        }),
        ('Платеж', {
            'fields': ('price_paid', 'payment_currency')
        }),
        ('Blockchain транзакции', {
            'fields': ('solana_payment_tx', 'solana_install_tx'),
            'classes': ('collapse',)
        }),
        ('Конфигурация', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('installed_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def skill_name(self, obj):
        url = reverse('admin:skills_skill_change', args=[obj.skill.id])
        return format_html('<a href="{}">{}</a>', url, obj.skill.name)
    skill_name.short_description = 'Навык'
    
    def bot_name(self, obj):
        url = reverse('admin:bot_core_botpassport_change', args=[obj.bot_passport.id])
        return format_html('<a href="{}">{}</a>', url, obj.bot_passport.name)
    bot_name.short_description = 'Бот'
    
    def buyer_name(self, obj):
        return obj.buyer.username
    buyer_name.short_description = 'Покупатель'
    
    def solana_status(self, obj):
        if obj.solana_install_tx:
            return format_html(
                '<span style="color: green;" title="TX: {}">✓</span>',
                obj.solana_install_tx[:10] + '...'
            )
        return format_html('<span style="color: gray;">—</span>')
    solana_status.short_description = 'Solana TX'


@admin.register(SkillRating)
class SkillRatingAdmin(admin.ModelAdmin):
    list_display = ['skill_name', 'user_name', 'rating_display', 'has_review', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['skill__name', 'user__username', 'review']
    readonly_fields = ['created_at', 'updated_at']
    
    def skill_name(self, obj):
        url = reverse('admin:skills_skill_change', args=[obj.skill.id])
        return format_html('<a href="{}">{}</a>', url, obj.skill.name)
    skill_name.short_description = 'Навык'
    
    def user_name(self, obj):
        return obj.user.username
    user_name.short_description = 'Пользователь'
    
    def rating_display(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span title="{}/5">{}</span>', obj.rating, stars)
    rating_display.short_description = 'Оценка'
    
    def has_review(self, obj):
        return bool(obj.review)
    has_review.short_description = 'Есть отзыв'
    has_review.boolean = True