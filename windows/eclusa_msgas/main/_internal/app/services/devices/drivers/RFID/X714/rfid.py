import asyncio


class RfidCommands:
    async def start_inventory(self):
        self.write("#READ:ON")

    async def stop_inventory(self):
        self.write("#READ:OFF")

    async def clear_tags(self):
        self.write("#CLEAR")

    async def config_reader(self):
        set_cmd = "#set_cmd:"

        # ANTENNAS
        antennas = self.config.get("ANT")
        for antenna in antennas:
            ant = antennas.get(antenna)
            ant_cmd = (
                f"|set_ant:{antenna},{ant.get('active')},{ant.get('power')},{abs(ant.get('rssi'))}"
            )
            set_cmd += ant_cmd

        # SESSION
        set_cmd += f"|SESSION:{self.config.get('SESSION')}"

        # START_READING
        set_cmd += f"|START_READING:{self.config.get('START_READING')}"

        # GPI_START
        set_cmd += f"|GPI_START:{self.config.get('GPI_START')}"

        # IGNORE_READ
        set_cmd += f"|IGNORE_READ:{self.config.get('IGNORE_READ')}"

        # ALWAYS_SEND
        set_cmd += f"|ALWAYS_SEND:{self.config.get('ALWAYS_SEND')}"

        # SIMPLE_SEND
        set_cmd += f"|SIMPLE_SEND:{self.config.get('SIMPLE_SEND')}"

        # KEYBOARD
        set_cmd += f"|KEYBOARD:{self.config.get('KEYBOARD')}"

        # BUZZER
        set_cmd += f"|BUZZER:{self.config.get('BUZZER')}"

        # DECODE_GTIN
        set_cmd += f"|DECODE_GTIN:{False}"

        set_cmd = set_cmd.lower()
        set_cmd = set_cmd.replace("true", "on").replace("false", "off")
        self.write(set_cmd)
        if self.config.get("START_READING", False):
            await self.start_inventory()
            self.is_reading = True
        else:
            await self.stop_inventory()
            self.is_reading = False

    async def auto_clear(self):
        while True:
            await asyncio.sleep(30)
            if self.is_connected:
                await self.clear_tags()
