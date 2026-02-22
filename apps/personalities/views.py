"""
DRF views for Personalities API.
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count
from django.shortcuts import get_object_or_404

from .models import (
    Personality,
    PersonalityCategory,
    PersonalityRating,
    PersonalityTemplate
)
from .serializers import (
    PersonalitySerializer,
    PersonalitySummarySerializer,
    PersonalityCreateSerializer,
    PersonalityCategorySerializer,
    PersonalityRatingSerializer,
    PersonalityRatingCreateSerializer,
    PersonalityTemplateSerializer,
    PersonalityInstallationSerializer,
    PersonalitySearchSerializer
)


class PersonalityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Personalities.
    
    Provides CRUD operations plus custom actions for:
    - Installing personalities on bots
    - Rating personalities
    - Searching personalities
    - Getting user's created personalities
    """
    
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'creator__username']
    ordering_fields = ['total_installations', 'price_ia_coin', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get personalities based on user permissions."""
        if self.action in ['list', 'retrieve']:
            # Public personalities for list/detail views
            return Personality.objects.filter(
                is_active=True,
                is_public=True
            ).select_related('creator').prefetch_related('category_memberships__category', 'ratings')
        
        # User's own personalities for other actions
        if self.request.user.is_authenticated:
            return Personality.objects.filter(
                creator=self.request.user
            ).select_related('creator').prefetch_related('category_memberships__category', 'ratings')
        
        return Personality.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return PersonalitySummarySerializer
        elif self.action == 'create':
            return PersonalityCreateSerializer
        elif self.action == 'install':
            return PersonalityInstallationSerializer
        elif self.action == 'rate':
            return PersonalityRatingCreateSerializer
        elif self.action == 'search':
            return PersonalitySearchSerializer
        return PersonalitySerializer
    
    def perform_create(self, serializer):
        """Set creator to current user."""
        serializer.save(creator=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def install(self, request, pk=None):
        """
        Install personality on a bot.
        
        POST /api/v1/personalities/{id}/install/
        {
            "bot_passport_id": "bot_123",
            "custom_prompt_override": "Optional custom prompt"
        }
        """
        personality = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            bot_passport = serializer.validated_data['bot_passport_id']
            custom_prompt = serializer.validated_data.get('custom_prompt_override', '')
            
            try:
                result = personality.install_on_bot(
                    user=request.user,
                    bot_passport=bot_passport,
                    custom_prompt_override=custom_prompt
                )
                
                if result['success']:
                    return Response({
                        'success': True,
                        'message': 'Personality installed successfully',
                        'installation_id': result.get('installation_id'),
                        'cost': result.get('cost', 0)
                    })
                else:
                    return Response({
                        'success': False,
                        'error': result['error']
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                return Response({
                    'success': False,
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def rate(self, request, pk=None):
        """
        Rate a personality.
        
        POST /api/v1/personalities/{id}/rate/
        {
            "rating": 5,
            "review": "Great personality!"
        }
        """
        personality = self.get_object()
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request, 'personality': personality}
        )
        
        if serializer.is_valid():
            # Check if user already rated this personality
            existing_rating = PersonalityRating.objects.filter(
                personality=personality,
                user=request.user
            ).first()
            
            if existing_rating:
                # Update existing rating
                for attr, value in serializer.validated_data.items():
                    setattr(existing_rating, attr, value)
                existing_rating.save()
                rating = existing_rating
            else:
                # Create new rating
                rating = serializer.save()
            
            return Response({
                'success': True,
                'rating': PersonalityRatingSerializer(rating).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def ratings(self, request, pk=None):
        """
        Get all ratings for a personality.
        
        GET /api/v1/personalities/{id}/ratings/
        """
        personality = self.get_object()
        ratings = personality.ratings.select_related('user').order_by('-created_at')
        
        # Pagination
        page = self.paginate_queryset(ratings)
        if page is not None:
            serializer = PersonalityRatingSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PersonalityRatingSerializer(ratings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """
        Advanced search for personalities.
        
        POST /api/v1/personalities/search/
        {
            "query": "helpful assistant",
            "category_ids": [1, 2],
            "min_rating": 4.0,
            "max_price": 100,
            "is_free": false,
            "sort_by": "popularity",
            "sort_order": "desc"
        }
        """
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            queryset = self.get_queryset()
            
            # Apply filters
            if data.get('query'):
                queryset = queryset.filter(
                    Q(name__icontains=data['query']) |
                    Q(description__icontains=data['query'])
                )
            
            if data.get('category_ids'):
                queryset = queryset.filter(
                    category_memberships__category__id__in=data['category_ids']
                ).distinct()
            
            if data.get('min_rating') is not None:
                queryset = queryset.annotate(
                    avg_rating=Avg('ratings__rating')
                ).filter(avg_rating__gte=data['min_rating'])
            
            if data.get('max_price') is not None:
                queryset = queryset.filter(price_ia_coin__lte=data['max_price'])
            
            if data.get('is_free'):
                queryset = queryset.filter(price_ia_coin=0)
            
            if data.get('creator_id'):
                queryset = queryset.filter(creator_id=data['creator_id'])
            
            # Apply sorting
            sort_by = data.get('sort_by', 'popularity')
            sort_order = data.get('sort_order', 'desc')
            
            sort_field = {
                'popularity': 'total_installations',  # Use installations as popularity proxy
                'rating': 'avg_rating',
                'price': 'price_ia_coin',
                'installations': 'total_installations',
                'created_at': 'created_at',
                'name': 'name'
            }.get(sort_by, 'total_installations')
            
            if sort_by == 'rating':
                queryset = queryset.annotate(avg_rating=Avg('ratings__rating'))
            
            if sort_order == 'desc':
                sort_field = f'-{sort_field}'
            
            queryset = queryset.order_by(sort_field)
            
            # Paginate results
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = PersonalitySummarySerializer(
                    page, 
                    many=True, 
                    context={'request': request}
                )
                return self.get_paginated_response(serializer.data)
            
            serializer = PersonalitySummarySerializer(
                queryset, 
                many=True, 
                context={'request': request}
            )
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_personalities(self, request):
        """
        Get current user's created personalities.
        
        GET /api/v1/personalities/my_personalities/
        """
        personalities = Personality.objects.filter(
            creator=request.user
        ).select_related('creator').prefetch_related('category_memberships__category', 'ratings')
        
        page = self.paginate_queryset(personalities)
        if page is not None:
            serializer = PersonalitySerializer(
                page, 
                many=True, 
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = PersonalitySerializer(
            personalities, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        Get featured personalities (high popularity/rating).
        
        GET /api/v1/personalities/featured/
        """
        personalities = self.get_queryset().filter(
            total_installations__gte=100,  # At least 100 installations
        ).order_by('-total_installations')[:20]
        
        serializer = PersonalitySummarySerializer(
            personalities, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)


class PersonalityCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Personality Categories (read-only).
    """
    
    queryset = PersonalityCategory.objects.filter(is_active=True).order_by('sort_order', 'name')
    serializer_class = PersonalityCategorySerializer
    
    @action(detail=True, methods=['get'])
    def personalities(self, request, pk=None):
        """
        Get personalities in this category.
        
        GET /api/v1/personality-categories/{id}/personalities/
        """
        category = self.get_object()
        personalities = Personality.objects.filter(
            category_memberships__category=category,
            is_active=True,
            is_public=True
        ).select_related('creator').prefetch_related('category_memberships__category', 'ratings')
        
        page = self.paginate_queryset(personalities)
        if page is not None:
            serializer = PersonalitySummarySerializer(
                page, 
                many=True, 
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        
        serializer = PersonalitySummarySerializer(
            personalities, 
            many=True, 
            context={'request': request}
        )
        return Response(serializer.data)


class PersonalityTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Personality Templates (read-only).
    """
    
    queryset = PersonalityTemplate.objects.filter(is_active=True).select_related('category')
    serializer_class = PersonalityTemplateSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category']
    search_fields = ['name', 'description']
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def use_template(self, request, pk=None):
        """
        Create a new personality from this template.
        
        POST /api/v1/personality-templates/{id}/use_template/
        {
            "name": "My Custom Personality",
            "description": "Based on template",
            "custom_values": {"key": "value"}
        }
        """
        template = self.get_object()
        
        name = request.data.get('name')
        description = request.data.get('description')
        custom_values = request.data.get('custom_values', {})
        
        if not name:
            return Response({
                'error': 'Name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            personality = template.create_personality(
                creator=request.user,
                name=name,
                description=description,
                custom_values=custom_values
            )
            
            serializer = PersonalitySerializer(
                personality, 
                context={'request': request}
            )
            return Response({
                'success': True,
                'personality': serializer.data
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)