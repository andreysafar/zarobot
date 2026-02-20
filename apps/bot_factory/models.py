from django.db import models
from django.conf import settings
import uuid

class Bot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bots')
    token = models.CharField(max_length=255, unique=True)
    container_id = models.CharField(max_length=255, blank=True, null=True)
    personality_uuid = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bot {self.id} for {self.owner}"
