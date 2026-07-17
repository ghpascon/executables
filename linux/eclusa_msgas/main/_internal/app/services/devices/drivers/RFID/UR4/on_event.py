import asyncio
import logging

from app.services.events import events


class OnEvent:
    async def on_received_cmd(self, data):
        if data[5] == 0x01:
            await self.on_success_cmd()

        if not self.setup:
            return
        await self.on_answer_command(data)

    async def on_success_cmd(self):
        if not self.setup and self.wait_answer:
            logging.info("SUCCESS", self.setup_step)
            self.setup_step += 1
            self.wait_answer = False

    async def on_answer_command(self, data):
        answer_command = data[4]

        # TAG
        if answer_command == 0x83:
            asyncio.create_task(self.on_tag(data))

        # GPI
        elif answer_command == 0xA2 and data[5] == 0x0A:
            asyncio.create_task(self.on_gpi(data))

        # TEMPERATURE
        elif answer_command == 0x35 and data[5] == 0x01:
            self.temperature = await self.decode_temperature(data)

        # CONNECTED ANTENNAS
        elif answer_command == 0x4F:
            logging.info(f"CONNECTED: {data[6]} -> {bin(data[6])}")

    async def on_tag(self, data, verbose=True):
        if not len(data) == 37 or not self.is_reading:
            return

        epc = "".join(f"{b:02X}" for b in data[7:19])  # string
        tid = "".join(f"{b:02X}" for b in data[19:31])  # string
        rssi = int((((data[31] << 8) | data[32]) - 0x10000) / 10)
        ant = data[33]  # int

        if rssi < self.config.get("ANT").get(f"{ant}").get("rssi"):
            return

        current_tag = {
            "device": self.device_name,
            "epc": epc,
            "tid": tid,
            "ant": ant,
            "rssi": rssi,
        }

        asyncio.create_task(events.on_tag(current_tag))

    async def on_gpi(self, data):
        gpi1 = data[6] == 0x01
        gpi2 = data[7] == 0x01
        if gpi1 == self.gpi["1"] and gpi2 == self.gpi["2"]:
            return
        elif not gpi1 == self.gpi["1"]:
            self.gpi["1"] = gpi1
            logging.info(f"GPI1 -> {gpi1}")
        elif not gpi2 == self.gpi["2"]:
            self.gpi["2"] = gpi2
            logging.info(f"GPI2 -> {gpi2}")

        if self.gpi_config is not None and self.gpi_config.get("active"):
            start = self.gpi_config.get("start")
            stop = self.gpi_config.get("stop")
            action = None

            if start.get("state") == self.gpi.get(f"{start.get('pin')}"):
                action = "start"

            if stop.get("state") == self.gpi.get(f"{stop.get('pin')}"):
                action = "stop"

            if action == "start":
                await self.start_inventory()
            elif action == "stop":
                await self.stop_inventory()
