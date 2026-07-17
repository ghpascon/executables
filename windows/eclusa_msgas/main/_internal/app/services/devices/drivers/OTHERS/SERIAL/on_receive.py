import logging

from app.services.events import events
from app.schemas.tag import TagSchema


class OnReceive:
    async def on_receive(self, data, verbose = False):
        if verbose:
            logging.info(f"{self.name} -> 📥 Received Data: {data}")

        # CHECK IF IS RFID TAG or OTHER EVENT
        try:
            tag = TagSchema(device=self.name, epc=data, tid=None, ant=None, rssi=None)
            await events.on_tag(tag.model_dump())
        except:
            await events.on_event(device=self.name, event_type=self.event_type, event_data=data)
