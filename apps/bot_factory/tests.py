from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import Bot, BotConfig

# Create your tests here.

class BotViewSetTests(APITestCase):
    """
    Tests for the BotViewSet.
    """
    def setUp(self):
        # Create two users
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')

        # Create a bot for user1
        self.bot1_config = BotConfig(
            personality='iya', 
            telegram_token='faketoken1', 
            telegram_username='fakebot1'
        )
        self.bot1 = Bot.objects.create(
            name='Test Bot 1',
            owner_id=self.user1.id,
            owner_wallet_address='wallet1',
            owner_telegram_id=12345,
            config=self.bot1_config
        )

        self.list_create_url = reverse('bot-list')
        self.detail_url = reverse('bot-detail', kwargs={'pk': str(self.bot1.id)})

    def test_create_bot(self):
        """
        Ensure we can create a new bot.
        """
        self.client.force_authenticate(user=self.user1)
        data = {
            "name": "New Bot",
            "description": "A shiny new bot",
            "config": {
                "telegram_token": "new_fake_token",
                "personality": "derValera"
            }
        }
        response = self.client.post(self.list_create_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Bot.objects.count(), 2)
        new_bot = Bot.objects.get(name="New Bot")
        self.assertEqual(new_bot.owner_id, self.user1.id)
        self.assertEqual(new_bot.config.telegram_token, "new_fake_token")

    def test_list_bots_for_owner(self):
        """
        Ensure user can list their own bots.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], self.bot1.name)

    def test_list_bots_for_other_user(self):
        """
        Ensure user cannot list bots they don't own.
        """
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_retrieve_own_bot(self):
        """
        Ensure user can retrieve their own bot.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.bot1.name)

    def test_cannot_retrieve_other_users_bot(self):
        """
        Ensure user cannot retrieve a bot they don't own.
        """
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(self.detail_url)
        # The IsOwner permission will deny access.
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_own_bot(self):
        """
        Ensure user can update their own bot.
        """
        self.client.force_authenticate(user=self.user1)
        data = {'name': 'Updated Name'}
        response = self.client.patch(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.bot1.reload()
        self.assertEqual(self.bot1.name, 'Updated Name')

    def test_update_bot_config(self):
        """
        Ensure user can update their bot's config.
        """
        self.client.force_authenticate(user=self.user1)
        data = {
            "config": {
                "personality": "neJry"
            }
        }
        response = self.client.patch(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.bot1.reload()
        self.assertEqual(self.bot1.config.personality, 'neJry')

    def test_cannot_update_other_users_bot(self):
        """
        Ensure user cannot update a bot they don't own.
        """
        self.client.force_authenticate(user=self.user2)
        data = {'name': 'Malicious Update'}
        response = self.client.patch(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_bot(self):
        """
        Ensure user can delete their own bot.
        """
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Bot.objects.count(), 0)

    def test_cannot_delete_other_users_bot(self):
        """
        Ensure user cannot delete a bot they don't own.
        """
        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Bot.objects.count(), 1)
