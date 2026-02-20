"""
Serializers for the Bot Factory app.

Since we are using MongoEngine, we cannot use ModelSerializer from DRF.
These serializers are written manually to handle the validation and
creation/update of Bot and BotConfig documents.
"""
from rest_framework import serializers
from core.models import Bot, BotConfig
from personalities.choices import PERSONALITY_CHOICES

class BotConfigSerializer(serializers.Serializer):
    """
    Serializer for the BotConfig embedded document.
    """
    telegram_token = serializers.CharField(max_length=100, write_only=True)
    personality = serializers.ChoiceField(choices=PERSONALITY_CHOICES, default='iya')
    prompt = serializers.CharField(style={'base_template': 'textarea.html'}, required=False)
    llm_model_name = serializers.CharField(max_length=100, required=False)

    def create(self, validated_data):
        # This method is not called directly, as it's an embedded document.
        # It's created as part of the parent Bot document.
        return BotConfig(**validated_data)

    def update(self, instance, validated_data):
        # This method is not called directly. It's updated as part of the parent.
        instance.telegram_token = validated_data.get('telegram_token', instance.telegram_token)
        instance.personality = validated_data.get('personality', instance.personality)
        instance.prompt = validated_data.get('prompt', instance.prompt)
        instance.llm_model_name = validated_data.get('llm_model_name', instance.llm_model_name)
        return instance

class BotSerializer(serializers.Serializer):
    """
    Serializer for the Bot document.
    """
    id = serializers.CharField(read_only=True)
    owner_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=500, required=False)
    ton_nft_address = serializers.CharField(max_length=100, read_only=True)
    config = BotConfigSerializer()

    def create(self, validated_data):
        config_data = validated_data.pop('config')
        
        # The owner_id is injected directly from the view's perform_create method.
        # The telegram_username will be fetched from telegram API later
        config_data['telegram_username'] = "temp_username"
        bot_config = BotConfig(**config_data)

        bot = Bot.objects.create(
            config=bot_config,
            **validated_data
        )
        return bot

    def update(self, instance, validated_data):
        config_data = validated_data.pop('config', {})
        
        # Update nested BotConfig
        if config_data:
            config_serializer = self.fields['config']
            config_instance = instance.config
            instance.config = config_serializer.update(config_instance, config_data)

        # Update Bot fields
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        
        instance.save()
        return instance 