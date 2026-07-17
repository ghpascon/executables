import asyncio
import logging

from app.services.events import events


class OnReceive:
    async def on_receive(self, data, verbose = False):
        data = data.decode(errors="ignore")
        data = data.replace("\r", "").replace("\n", "")
        data = data.lower()
        if verbose:
            logging.info(f"{self.name} -> 📥 Received Data: {data}")

        if data.startswith("#read:"):
            self.is_reading = data.endswith("on")
            if self.is_reading:
                await self.clear_tags()
                await events.on_start(self.name)
            else:
                await events.on_stop(self.name)

        elif data.startswith("#t+@"):
            tag = data[4:]
            epc, tid, ant, rssi = tag.split("|")
            current_tag = {
                "device": self.name,
                "epc": epc,
                "tid": tid,
                "ant": int(ant),
                "rssi": int(rssi) * (-1),
            }
            asyncio.create_task(events.on_tag(current_tag))

        elif len(data) == 24:
            current_tag = {
                "device": self.name,
                "epc": data,
                "tid": None,
                "ant": 1,
                "rssi": 0,
            }
            asyncio.create_task(events.on_tag(current_tag))

        elif data.startswith("#set_cmd:"):
            logging.info(f"CONFIG -> {data[data.index(':')+1:]}")
