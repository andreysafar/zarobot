"""
URL configuration for Personalities app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PersonalityViewSet,
    PersonalityCategoryViewSet,
    PersonalityTemplateViewSet
)

# Create router for API endpoints
router = DefaultRouter()
router.register(r'personalities', PersonalityViewSet, basename='personality')
router.register(r'personality-categories', PersonalityCategoryViewSet, basename='personality-category')
router.register(r'personality-templates', PersonalityTemplateViewSet, basename='personality-template')

# URL patterns
urlpatterns = [
    # API v1 endpoints
    path('api/v1/', include(router.urls)),
]

# Named URL patterns for easy reversal
app_name = 'personalities'