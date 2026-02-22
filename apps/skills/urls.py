"""
Skills app URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SkillCategoryViewSet, SkillViewSet, SkillInstallationViewSet, SkillRatingViewSet

app_name = 'skills'

router = DefaultRouter()
router.register(r'categories', SkillCategoryViewSet, basename='skill-category')
router.register(r'skills', SkillViewSet, basename='skill')
router.register(r'installations', SkillInstallationViewSet, basename='skill-installation')
router.register(r'ratings', SkillRatingViewSet, basename='skill-rating')

urlpatterns = [
    path('', include(router.urls)),
]