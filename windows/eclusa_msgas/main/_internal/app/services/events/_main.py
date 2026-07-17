import logging
from collections import deque

from .on_event import OnEvent
from .users import Users
from app.core.settings import settings

class Events(OnEvent, Users):
    def __init__(self):
        """
        Initialize the Events manager.
        """
        self.tags = {}  # Active tags currently detected
        self.events = deque(maxlen=20)  # Store the last 20 events
        self.actions = {}  # Registered actions
        self.user_id = None
        self.card_id = None
        self.is_open = False
        self.msgas_api_url = settings.data.get("MSGAS_API_URL", "https://api.msgas.com.br/rest01/api/integracao/v1")

    async def clear_tags(self, device: str | None = None):
        """
        Clear tags from memory.
        """
        if device is None:
            self.tags = {}
            logging.info("[ CLEAR ] -> All TAGS")
            return

        # Keep only tags not belonging to the specified device
        self.tags = {k: v for k, v in self.tags.items() if v.get("device") != device}
        logging.info(f"[ CLEAR ] -> Reader: {device}")


events = Events()
