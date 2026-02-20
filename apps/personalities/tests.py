from django.test import TestCase
from .models import Personality
from .echo import EchoPersonality

class EchoPersonalityIntegrationTest(TestCase):
    fixtures = ['initial_data.json']

    def test_echo_personality_flow(self):
        """
        Tests the full flow of retrieving the Echo personality
        and using it to handle a message.
        """
        # 1. Retrieve the Echo Personality from the database
        try:
            echo_personality_model = Personality.objects.get(name="Echo")
        except Personality.DoesNotExist:
            self.fail("The Echo Personality fixture did not load correctly.")

        # 2. Instantiate the EchoPersonality class
        echo_class_instance = EchoPersonality()

        # 3. Handle a message using the class
        input_message = "Hello, this is a test."
        output_message = echo_class_instance.handle_message(input_message)

        # 4. Assert the output is as expected
        self.assertEqual(output_message, f"Echo: {input_message}")
        self.assertEqual(echo_personality_model.price, 0.00) 