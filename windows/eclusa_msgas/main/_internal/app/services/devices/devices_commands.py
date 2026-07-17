from ..events import events


class DevicesCommands:
    async def start_inventory(self, device: str | None):
        await self.devices[device].start_inventory()

    async def stop_inventory(self, device: str | None):
        await self.devices[device].stop_inventory()

    async def clear_tags(self, device: str | None = None):
        await events.clear_tags(device)

    async def write_gpo(
        self,
        device: str,
        pin: int = 1,
        state: bool | str = True,
        control: str = "static",
        time: int = 1000,
    ):
        if hasattr(self.devices[device], "write_gpo"):
            await self.devices[device].write_gpo(pin=pin, state=state, control=control, time=time)
            return True
        return False
