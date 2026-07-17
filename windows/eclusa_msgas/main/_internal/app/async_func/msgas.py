import asyncio
from app.services.events import events
from app.core.settings import settings

async def get_descriptions():
    while True:
        await asyncio.sleep(1)
        if not events.tags:
            continue
        missing_info = [tag.get("epc") for tag in events.tags.values() if tag.get("info") is None and tag.get("epc") is not None]

        payload = {
            "device": settings.data.get("DEVICE_NAME", "UnknownDevice"),
            "tags": missing_info
        }

        await events.fetch_descriptions(payload)