"""
Django admin configuration for Personalities models.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Personality, 
    PersonalityCategory, 
    PersonalityCategoryMembership,
    PersonalityRating,
    PersonalityTemplate
)


class PersonalityCategoryMembershipInline(admin.TabularInline):
    """Inline for personality categories."""
    model = PersonalityCategoryMembership
    extra = 1


class PersonalityRatingInline(admin.TabularInline):
    """Inline for personality ratings."""
    model = PersonalityRating
    extra = 0
    readonly_fields = ['user', 'rating', 'created_at']


@admin.register(Personality)
class PersonalityAdmin(admin.ModelAdmin):
    """Admin interface for Personalities."""
    
    list_display = [
        'name',
        'creator',
        'price_display',
        'installations_count',
        'revenue_display',
        'popularity_display',
        'is_active',
        'is_public',
        'created_at'
    ]
    
    list_filter = [
        'is_active',
        'is_public',
        'is_system',
        'price_ia_coin',
        'created_at',
        'category_memberships__category',
    ]
    
    search_fields = [
        'name',
        'description',
        'creator__username',
        'system_prompt',
    ]
    
    readonly_fields = [
        'personality_id',
        'total_installations',
        'total_revenue',
        'popularity_display',
        'created_at',
        'updated_at',
    ]
    
    inlines = [PersonalityCategoryMembershipInline, PersonalityRatingInline]
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'creator']
        }),
        ('Prompt System', {
            'fields': ['system_prompt', 'langflow_flow_id']
        }),
        ('Economics', {
            'fields': ['price_ia_coin']
        }),
        ('Status & Visibility', {
            'fields': ['is_active', 'is_public', 'is_system']
        }),
        ('Metadata', {
            'fields': ['metadata'],
            'classes': ['collapse']
        }),
        ('Statistics', {
            'fields': [
                'total_installations', 
                'total_revenue',
                'popularity_display'
            ],
            'classes': ['collapse']
        }),
        ('System Fields', {
            'fields': ['personality_id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    def price_display(self, obj):
        """Display formatted price."""
        if obj.is_free:
            return format_html('<span style="color: green;">Free</span>')
        return f"{obj.price_ia_coin} IA"
    price_display.short_description = "Price"
    price_display.admin_order_field = 'price_ia_coin'
    
    def installations_count(self, obj):
        """Display installation count with formatting."""
        count = obj.total_installations
        if count >= 1000:
            return f"{count/1000:.1f}K"
        return str(count)
    installations_count.short_description = "Installs"
    installations_count.admin_order_field = 'total_installations'
    
    def revenue_display(self, obj):
        """Display formatted revenue."""
        if obj.total_revenue == 0:
            return "-"
        return f"{obj.total_revenue} IA"
    revenue_display.short_description = "Revenue"
    revenue_display.admin_order_field = 'total_revenue'
    
    def popularity_display(self, obj):
        """Display popularity score with visual indicator."""
        score = obj.popularity_score
        stars = "★" * int(score) + "☆" * (10 - int(score))
        return format_html(
            '<span title="Popularity: {:.1f}/10">{}</span>',
            score,
            stars[:5]  # Show only first 5 stars
        )
    popularity_display.short_description = "Popularity"


@admin.register(PersonalityCategory)
class PersonalityCategoryAdmin(admin.ModelAdmin):
    """Admin interface for Personality Categories."""
    
    list_display = [
        'name',
        'color_display',
        'personality_count',
        'is_active',
        'sort_order',
        'created_at'
    ]
    
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']
    
    def color_display(self, obj):
        """Display color with visual indicator."""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; display: inline-block;"></div> {}',
            obj.color,
            obj.color
        )
    color_display.short_description = "Color"
    
    def personality_count(self, obj):
        """Display number of personalities in category."""
        return obj.personality_memberships.count()
    personality_count.short_description = "Personalities"


@admin.register(PersonalityRating)
class PersonalityRatingAdmin(admin.ModelAdmin):
    """Admin interface for Personality Ratings."""
    
    list_display = [
        'personality',
        'user',
        'rating_display',
        'has_review',
        'created_at'
    ]
    
    list_filter = [
        'rating',
        'created_at',
        'personality__name',
    ]
    
    search_fields = [
        'personality__name',
        'user__username',
        'review',
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    def rating_display(self, obj):
        """Display rating with stars."""
        stars = "★" * obj.rating + "☆" * (5 - obj.rating)
        return format_html('<span title="{}/5 stars">{}</span>', obj.rating, stars)
    rating_display.short_description = "Rating"
    rating_display.admin_order_field = 'rating'
    
    def has_review(self, obj):
        """Check if rating has review text."""
        return bool(obj.review)
    has_review.boolean = True
    has_review.short_description = "Has Review"


@admin.register(PersonalityTemplate)
class PersonalityTemplateAdmin(admin.ModelAdmin):
    """Admin interface for Personality Templates."""
    
    list_display = [
        'name',
        'category',
        'usage_count',
        'is_active',
        'created_at'
    ]
    
    list_filter = [
        'is_active',
        'category',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'description',
        'system_prompt_template',
    ]
    
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'category']
        }),
        ('Template Content', {
            'fields': ['system_prompt_template', 'metadata_template']
        }),
        ('Status & Statistics', {
            'fields': ['is_active', 'usage_count']
        }),
        ('System Fields', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]


# Register the through model for better admin experience
@admin.register(PersonalityCategoryMembership)
class PersonalityCategoryMembershipAdmin(admin.ModelAdmin):
    """Admin interface for Personality Category Memberships."""
    
    list_display = ['personality', 'category', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['personality__name', 'category__name']