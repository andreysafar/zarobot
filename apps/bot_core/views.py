"""
API views for Bot Core models.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import BotPassport, BotState, SkillInstallation, PersonalityInstance
from .serializers import (
    BotPassportSerializer,
    BotPassportCreateSerializer,
    BotPassportSummarySerializer,
    BotStateSerializer,
    SkillInstallationSerializer,
    PersonalityInstanceSerializer,
)


class BotPassportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Bot Passport CRUD operations.
    """
    
    queryset = BotPassport.objects.select_related('owner').all()  # 'personality' to be added later
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return BotPassportCreateSerializer
        elif self.action == 'list':
            return BotPassportSummarySerializer
        else:
            return BotPassportSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        
        # Superusers can see all bots
        if user.is_superuser:
            return self.queryset
        
        # Regular users can only see their own bots
        return self.queryset.filter(owner=user)
    
    def perform_create(self, serializer):
        """Set owner to current user when creating."""
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_experience(self, request, pk=None):
        """Add experience points to a bot."""
        bot = self.get_object()
        
        # Validate input
        xp_amount = request.data.get('xp_amount')
        if not isinstance(xp_amount, int) or xp_amount <= 0:
            return Response(
                {'error': 'xp_amount must be a positive integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add experience
        old_level = bot.training_level
        bot.add_experience(xp_amount)
        bot.refresh_from_db()
        
        # Check if leveled up
        leveled_up = bot.training_level > old_level
        
        return Response({
            'experience_points': bot.experience_points,
            'training_level': bot.training_level,
            'leveled_up': leveled_up,
            'training_progress': bot.get_training_progress(),
            'can_level_up': bot.can_level_up(),
        })
    
    @action(detail=True, methods=['post'])
    def level_up(self, request, pk=None):
        """Manually level up a bot if possible."""
        bot = self.get_object()
        
        if bot.level_up():
            return Response({
                'success': True,
                'training_level': bot.training_level,
                'experience_points': bot.experience_points,
                'training_progress': bot.get_training_progress(),
                'can_level_up': bot.can_level_up(),
            })
        else:
            return Response(
                {'error': 'Bot cannot level up (insufficient XP or max level reached)'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def state(self, request, pk=None):
        """Get bot state information."""
        bot = self.get_object()
        
        try:
            bot_state = bot.local_state
            serializer = BotStateSerializer(bot_state)
            return Response(serializer.data)
        except BotState.DoesNotExist:
            return Response(
                {'error': 'Bot state not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def sync_blockchain(self, request, pk=None):
        """Trigger blockchain synchronization for bot."""
        bot = self.get_object()
        
        # TODO: Implement actual blockchain sync
        # For now, just mark as pending sync
        try:
            bot_state = bot.local_state
            bot_state.mark_for_sync()
            
            return Response({
                'success': True,
                'message': 'Blockchain sync initiated',
                'sync_status': bot_state.sync_status,
            })
        except BotState.DoesNotExist:
            return Response(
                {'error': 'Bot state not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class BotStateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Bot State operations.
    """
    
    queryset = BotState.objects.select_related('passport').all()  # 'active_prompt' to be added later
    serializer_class = BotStateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        
        # Superusers can see all bot states
        if user.is_superuser:
            return self.queryset
        
        # Regular users can only see their own bots' states
        return self.queryset.filter(passport__owner=user)
    
    @action(detail=True, methods=['post'])
    def mark_synced(self, request, pk=None):
        """Mark bot state as synced with blockchain."""
        bot_state = self.get_object()
        bot_state.mark_synced()
        
        return Response({
            'success': True,
            'sync_status': bot_state.sync_status,
            'last_synced_at': bot_state.last_synced_at,
        })
    
    @action(detail=True, methods=['post'])
    def update_context(self, request, pk=None):
        """Update conversation context."""
        bot_state = self.get_object()
        
        new_context = request.data.get('conversation_context')
        if not isinstance(new_context, dict):
            return Response(
                {'error': 'conversation_context must be a valid JSON object'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate context size
        import json
        context_size = len(json.dumps(new_context).encode('utf-8'))
        if context_size > 512 * 1024:  # 512KB limit
            return Response(
                {'error': 'Conversation context exceeds 512KB limit'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        bot_state.conversation_context = new_context
        bot_state.mark_for_sync()  # Mark for blockchain sync
        bot_state.save()
        
        return Response({
            'success': True,
            'conversation_context': bot_state.conversation_context,
            'sync_status': bot_state.sync_status,
        })


class SkillInstallationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Skill Installation operations.
    """
    
    queryset = SkillInstallation.objects.select_related('passport').all()
    serializer_class = SkillInstallationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        
        # Filter by bot passport parameter if provided
        passport_id = self.request.query_params.get('passport_id')
        queryset = self.queryset
        
        if passport_id:
            queryset = queryset.filter(passport__bot_id=passport_id)
        
        # Superusers can see all installations
        if user.is_superuser:
            return queryset
        
        # Regular users can only see their own bots' installations
        return queryset.filter(passport__owner=user)


class PersonalityInstanceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Personality Instance operations.
    """
    
    queryset = PersonalityInstance.objects.select_related('passport').all()
    serializer_class = PersonalityInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        user = self.request.user
        
        # Filter by bot passport parameter if provided
        passport_id = self.request.query_params.get('passport_id')
        queryset = self.queryset
        
        if passport_id:
            queryset = queryset.filter(passport__bot_id=passport_id)
        
        # Superusers can see all personality instances
        if user.is_superuser:
            return queryset
        
        # Regular users can only see their own bots' personality instances
        return queryset.filter(passport__owner=user)