"""
Django admin configuration for Bot Core models.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import BotPassport, BotState, SkillInstallation, PersonalityInstance


@admin.register(BotPassport)
class BotPassportAdmin(admin.ModelAdmin):
    """Admin interface for Bot Passports."""
    
    list_display = [
        'name', 
        'owner', 
        'training_level', 
        'experience_points',
        'blockchain_status',
        'is_active', 
        'created_at'
    ]
    
    list_filter = [
        'is_active',
        'training_level',
        'created_at',
        # 'personality',  # To be added when personalities app is created
    ]
    
    search_fields = [
        'name',
        'bot_id',
        'owner__username',
        'solana_nft_address',
        'ton_nft_address',
    ]
    
    readonly_fields = [
        'bot_id',
        'created_at',
        'updated_at',
        'marketplace_value_multiplier',
        'training_progress_display',
    ]
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'owner', 'is_active']
        }),
        ('Blockchain Addresses', {
            'fields': ['solana_nft_address', 'ton_nft_address'],
            'classes': ['collapse']
        }),
        ('Training & Experience', {
            'fields': [
                'training_level', 
                'experience_points',
                'training_progress_display',
                'marketplace_value_multiplier'
            ]
        }),
        # ('Personality & Skills', {
        #     'fields': ['personality'],
        # }),
        ('State & Metadata', {
            'fields': ['state'],
            'classes': ['collapse']
        }),
        ('System Fields', {
            'fields': ['bot_id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def blockchain_status(self, obj):
        """Display blockchain synchronization status."""
        solana_status = "✅" if obj.solana_nft_address else "❌"
        ton_status = "✅" if obj.ton_nft_address else "❌"
        return format_html(
            "Solana: {} | TON: {}",
            solana_status,
            ton_status
        )
    blockchain_status.short_description = "Blockchain Status"
    
    def training_progress_display(self, obj):
        """Display training progress bar."""
        progress = obj.get_training_progress()
        percentage = int(progress * 100)
        
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: #28a745; height: 20px; border-radius: 3px; text-align: center; color: white; font-size: 12px; line-height: 20px;">'
            '{}%'
            '</div></div>',
            percentage,
            percentage
        )
    training_progress_display.short_description = "Training Progress"


@admin.register(BotState)
class BotStateAdmin(admin.ModelAdmin):
    """Admin interface for Bot States."""
    
    list_display = [
        'passport_name',
        'sync_status',
        # 'active_prompt',  # To be added when prompts app is created
        'last_synced_at',
        'updated_at'
    ]
    
    list_filter = [
        'sync_status',
        'last_synced_at',
        'created_at',
    ]
    
    search_fields = [
        'passport__name',
        'passport__bot_id',
        'training_data_hash',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = [
        ('Bot Reference', {
            'fields': ['passport']
        }),
        # ('Active Configuration', {
        #     'fields': ['active_prompt']
        # }),
        ('Conversation State', {
            'fields': ['conversation_context'],
            'classes': ['collapse']
        }),
        ('Training Data', {
            'fields': ['training_data_hash'],
        }),
        ('Synchronization', {
            'fields': ['sync_status', 'last_synced_at']
        }),
        ('System Fields', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def passport_name(self, obj):
        """Display passport name."""
        return obj.passport.name
    passport_name.short_description = "Bot Name"
    passport_name.admin_order_field = 'passport__name'


@admin.register(SkillInstallation)
class SkillInstallationAdmin(admin.ModelAdmin):
    """Admin interface for Skill Installations."""
    
    list_display = [
        'passport_name',
        # 'skill_name',  # To be added when skills app is created
        'installed_at',
        'is_active'
    ]
    
    list_filter = [
        'is_active',
        'installed_at',
    ]
    
    search_fields = [
        'passport__name',
        'passport__bot_id',
        # 'skill__name',  # To be added later
    ]
    
    readonly_fields = [
        'installed_at',
    ]
    
    def passport_name(self, obj):
        """Display passport name."""
        return obj.passport.name
    passport_name.short_description = "Bot Name"
    passport_name.admin_order_field = 'passport__name'


@admin.register(PersonalityInstance)
class PersonalityInstanceAdmin(admin.ModelAdmin):
    """Admin interface for Personality Instances."""
    
    list_display = [
        'passport_name',
        # 'personality_name',  # To be added when personalities app is created
        'has_custom_prompt',
        'activated_at',
        'is_active'
    ]
    
    list_filter = [
        'is_active',
        'activated_at',
    ]
    
    search_fields = [
        'passport__name',
        'passport__bot_id',
        # 'personality__name',  # To be added later
    ]
    
    readonly_fields = [
        'activated_at',
    ]
    
    def passport_name(self, obj):
        """Display passport name."""
        return obj.passport.name
    passport_name.short_description = "Bot Name"
    passport_name.admin_order_field = 'passport__name'
    
    def has_custom_prompt(self, obj):
        """Check if instance has custom prompt override."""
        return bool(obj.custom_prompt_override)
    has_custom_prompt.boolean = True
    has_custom_prompt.short_description = "Custom Prompt"