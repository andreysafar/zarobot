"""
Views for the Bot Factory app.
"""
from rest_framework import viewsets, permissions
from core.models import Bot
from .serializers import BotSerializer
from .permissions import IsOwner

# Create your views here.

class BotViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows bots to be viewed or edited.
    """
    serializer_class = BotSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        """
        This view should return a list of all the bots
        for the currently authenticated user.
        """
        return Bot.objects.filter(owner_id=self.request.user.id)

    def perform_create(self, serializer):
        """
        Inject the owner_id into the serializer.
        """
        serializer.save(owner_id=self.request.user.id)

    def get_serializer_context(self):
        """
        Pass the request context to the serializer.
        """
        return {'request': self.request}
