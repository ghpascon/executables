import asyncio

from app.services.events import events


class RfidCommands:
    async def loop(self):
        while True:
            await asyncio.sleep(0.3 if not self.is_reading else 0.15)
            if self.step == 0:
                await self.config_reader()
            elif self.step == 1:
                await self.set_band()
            elif self.step == 2:
                await self.set_power()
            else:
                self.is_connected = True
                asyncio.create_task(events.on_connect(self.name))
                await self.inventory_cmd()

    async def inventory_cmd(self):
        if not self.is_reading:
            return
        cmd = bytes([0x09, 0x00, 0x01, 0x04, self.session, 0x00, 0x80, 0x0A, 0x00, 0x00])
        self.write(cmd, False)

    async def start_inventory(self):
        self.is_reading = True
        await events.on_start(self.name)

    async def stop_inventory(self):
        self.is_reading = False
        await events.on_stop(self.name)

    async def config_reader(self):
        cmd = bytes([0x04, 0xFF, 0x21, 0x00, 0x00])
        self.write(cmd, False)

    async def set_band(self):
        cmd = bytes([0x06, 0x00, 0x22, 0xE2, 0x40, 0x00, 0x00])
        self.write(cmd, False)

    async def set_power(self):
        cmd = bytes([0x05, 0x00, 0x2F, self.power, 0x00, 0x00])
        self.write(cmd, False)
