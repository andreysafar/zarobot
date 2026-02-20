class EchoPersonality:
    """
    A simple personality that echoes back any message it receives.
    """
    def handle_message(self, message_text: str) -> str:
        """
        Takes a message text and returns it with a prefix.

        Args:
            message_text: The input message string.

        Returns:
            The echoed message string.
        """
        return f"Echo: {message_text}" 