"""
URL configuration for Bot Core app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BotPassportViewSet,
    BotStateViewSet,
    SkillInstallationViewSet,
    PersonalityInstanceViewSet,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'passports', BotPassportViewSet, basename='botpassport')
router.register(r'states', BotStateViewSet, basename='botstate')
router.register(r'skill-installations', SkillInstallationViewSet, basename='skillinstallation')
router.register(r'personality-instances', PersonalityInstanceViewSet, basename='personalityinstance')

app_name = 'bot_core'

urlpatterns = [
    path('api/v1/bot-core/', include(router.urls)),
]