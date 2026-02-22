"""
Skills app views
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.utils import timezone

from .models import SkillCategory, Skill, SkillInstallation, SkillRating
from .serializers import (
    SkillCategorySerializer, SkillCategoryCreateSerializer,
    SkillSerializer, SkillSummarySerializer, SkillCreateSerializer,
    SkillInstallationSerializer, SkillInstallationCreateSerializer,
    SkillRatingSerializer, SkillRatingCreateSerializer,
    SkillSearchSerializer, SkillPublishSerializer
)


class SkillCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet для категорий навыков"""
    
    queryset = SkillCategory.objects.filter(is_active=True)
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['sort_order', 'name']
    ordering = ['sort_order', 'name']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SkillCategoryCreateSerializer
        return SkillCategorySerializer
    
    @action(detail=True, methods=['get'])
    def skills(self, request, pk=None):
        """Получить навыки категории"""
        category = self.get_object()
        skills = Skill.objects.filter(
            category=category,
            is_public=True,
            status='active'
        ).select_related('creator', 'category')
        
        serializer = SkillSummarySerializer(skills, many=True, context={'request': request})
        return Response(serializer.data)


class SkillViewSet(viewsets.ModelViewSet):
    """ViewSet для навыков"""
    
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'tags']
    filterset_fields = ['category', 'execution_type', 'is_free', 'status']
    ordering_fields = [
        'created_at', 'price_ia_coins', 'total_installations', 
        'average_rating'
    ]
    ordering = ['-total_installations', '-average_rating', '-created_at']
    
    def get_queryset(self):
        """Получить навыки в зависимости от действия"""
        if self.action in ['list', 'retrieve']:
            # Публичные навыки для всех
            return Skill.objects.filter(
                is_public=True,
                status='active'
            ).select_related('creator', 'category').prefetch_related('ratings')
        elif self.action == 'my_skills':
            # Навыки пользователя
            return Skill.objects.filter(
                creator=self.request.user
            ).select_related('category').prefetch_related('ratings')
        else:
            # Все навыки для создания/редактирования
            return Skill.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SkillCreateSerializer
        elif self.action in ['list', 'my_skills', 'featured', 'search']:
            return SkillSummarySerializer
        elif self.action == 'publish':
            return SkillPublishSerializer
        return SkillSerializer
    
    def perform_create(self, serializer):
        """Создание навыка"""
        serializer.save(creator=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_skills(self, request):
        """Мои навыки"""
        skills = self.get_queryset()
        page = self.paginate_queryset(skills)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(skills, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Популярные навыки"""
        skills = self.get_queryset().annotate(
            popularity=Count('installations') + Avg('ratings__rating')
        ).order_by('-popularity', '-total_installations')[:20]
        
        serializer = self.get_serializer(skills, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """Расширенный поиск навыков"""
        search_serializer = SkillSearchSerializer(data=request.data)
        search_serializer.is_valid(raise_exception=True)
        
        data = search_serializer.validated_data
        queryset = self.get_queryset()
        
        # Фильтрация по запросу
        if data.get('query'):
            query = data['query']
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(tags__icontains=query)
            )
        
        # Фильтрация по категории
        if data.get('category'):
            queryset = queryset.filter(category_id=data['category'])
        
        # Фильтрация по цене
        if data.get('min_price') is not None:
            queryset = queryset.filter(price_ia_coins__gte=data['min_price'])
        if data.get('max_price') is not None:
            queryset = queryset.filter(price_ia_coins__lte=data['max_price'])
        
        # Фильтрация по рейтингу
        if data.get('min_rating'):
            queryset = queryset.filter(average_rating__gte=data['min_rating'])
        
        # Фильтрация по типу выполнения
        if data.get('execution_type'):
            queryset = queryset.filter(execution_type=data['execution_type'])
        
        # Фильтрация по тегам
        if data.get('tags'):
            for tag in data['tags']:
                queryset = queryset.filter(tags__icontains=tag)
        
        # Фильтрация по бесплатности
        if data.get('is_free') is not None:
            queryset = queryset.filter(is_free=data['is_free'])
        
        # Сортировка
        sort_by = data.get('sort_by', 'popularity')
        if sort_by == 'popularity':
            queryset = queryset.order_by('-total_installations', '-average_rating')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-average_rating', '-total_installations')
        elif sort_by == 'price_asc':
            queryset = queryset.order_by('price_ia_coins', 'name')
        elif sort_by == 'price_desc':
            queryset = queryset.order_by('-price_ia_coins', 'name')
        elif sort_by == 'installations':
            queryset = queryset.order_by('-total_installations', '-created_at')
        elif sort_by == 'created_at':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'name':
            queryset = queryset.order_by('name')
        
        # Пагинация
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def install(self, request, pk=None):
        """Установка навыка на бота"""
        skill = self.get_object()
        
        # Проверка данных
        bot_passport_id = request.data.get('bot_passport_id')
        if not bot_passport_id:
            return Response(
                {'error': 'bot_passport_id обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Создание установки
        install_data = {
            'skill_id': skill.id,
            'bot_passport_id': bot_passport_id,
            'config': request.data.get('config', {})
        }
        
        serializer = SkillInstallationCreateSerializer(
            data=install_data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        installation = serializer.save()
        
        # TODO: Запустить обработку установки через Solana
        # await installation.process_installation()
        
        return Response(
            SkillInstallationSerializer(installation, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        """Оценка навыка"""
        skill = self.get_object()
        
        rating_data = {
            'skill_id': skill.id,
            'rating': request.data.get('rating'),
            'review': request.data.get('review', '')
        }
        
        serializer = SkillRatingCreateSerializer(
            data=rating_data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        rating = serializer.save()
        
        return Response(
            SkillRatingSerializer(rating, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Публикация навыка в маркетплейс"""
        skill = self.get_object()
        
        # Проверка прав
        if skill.creator != request.user:
            return Response(
                {'error': 'Вы не являетесь создателем этого навыка'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        publish_data = {
            'skill_id': skill.id,
            'solana_private_key': request.data.get('solana_private_key')
        }
        
        serializer = SkillPublishSerializer(
            data=publish_data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            # Обновление статуса
            skill.status = 'pending_review'
            skill.save(update_fields=['status'])
            
            # TODO: Регистрация в Solana Registry
            # if serializer.validated_data.get('solana_private_key'):
            #     await skill.register_on_solana(
            #         private_key=serializer.validated_data['solana_private_key']
            #     )
            
            return Response({
                'message': 'Навык отправлен на модерацию',
                'status': skill.status
            })
            
        except Exception as e:
            return Response(
                {'error': f'Ошибка публикации: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def installations(self, request, pk=None):
        """Установки навыка"""
        skill = self.get_object()
        installations = SkillInstallation.objects.filter(
            skill=skill
        ).select_related('bot_passport', 'buyer')
        
        serializer = SkillInstallationSerializer(
            installations, many=True, context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def ratings(self, request, pk=None):
        """Оценки навыка"""
        skill = self.get_object()
        ratings = SkillRating.objects.filter(
            skill=skill
        ).select_related('user').order_by('-created_at')
        
        serializer = SkillRatingSerializer(
            ratings, many=True, context={'request': request}
        )
        return Response(serializer.data)


class SkillInstallationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для установок навыков"""
    
    serializer_class = SkillInstallationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'is_enabled', 'payment_currency']
    ordering_fields = ['installed_at', 'price_paid']
    ordering = ['-installed_at']
    
    def get_queryset(self):
        """Только установки пользователя"""
        return SkillInstallation.objects.filter(
            buyer=self.request.user
        ).select_related('skill', 'bot_passport')
    
    @action(detail=True, methods=['post'])
    def toggle_enabled(self, request, pk=None):
        """Включить/выключить навык"""
        installation = self.get_object()
        
        if installation.buyer != request.user:
            return Response(
                {'error': 'Нет прав доступа'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        installation.is_enabled = not installation.is_enabled
        installation.save(update_fields=['is_enabled'])
        
        return Response({
            'is_enabled': installation.is_enabled,
            'message': 'Навык включен' if installation.is_enabled else 'Навык выключен'
        })
    
    @action(detail=True, methods=['put'])
    def update_config(self, request, pk=None):
        """Обновить конфигурацию навыка"""
        installation = self.get_object()
        
        if installation.buyer != request.user:
            return Response(
                {'error': 'Нет прав доступа'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_config = request.data.get('config', {})
        installation.config = new_config
        installation.save(update_fields=['config'])
        
        return Response({
            'config': installation.config,
            'message': 'Конфигурация обновлена'
        })


class SkillRatingViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для оценок навыков"""
    
    serializer_class = SkillRatingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['rating']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Только оценки пользователя"""
        return SkillRating.objects.filter(
            user=self.request.user
        ).select_related('skill')