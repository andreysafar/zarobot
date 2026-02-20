"""
URL configuration for the Bot Factory app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BotViewSet

router = DefaultRouter()
router.register(r'bots', BotViewSet, basename='bot')

urlpatterns = [
    path('', include(router.urls)),
] 