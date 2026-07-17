import logging

from app.services.events import events


class OnReceive:
    async def on_receive(self, data):
        # Converte cada byte em hexadecimal
        hex_list = [f"0x{b:02X}" for b in data]
        # logging.info(f"{self.name} -> 📥 Received Data: {hex_list}")
        current_cmd = hex_list[2]

        # CONFIG
        if current_cmd == "0x21":
            logging.info(f"{self.name} MODULE CONNECTED")
            self.step = 1
        # BAND
        elif current_cmd == "0x22":
            logging.info(f"{self.name} BAND")
            self.step = 2
        # POWER
        elif current_cmd == "0x2F":
            logging.info(f"{self.name} POWER")
            self.step = 3
            if self.config.get("START_READING"):
                await self.start_inventory()
        elif current_cmd == "0x01":
            await self.on_tag_cmd(hex_list)

    async def on_tag_cmd(self, data):
        if len(data) > 20:
            data = data[7:]
        else:
            return

        while True:
            if len(data) < 15:
                break
            epc = "".join(data[:12]).replace("0x", "")
            # rssi_hex_str = data[13]
            # rssi_val = int(rssi_hex_str, 16)

            # if rssi_val >= 0x80:
            #     rssi_val -= 0x100

            data = data[14:]
            await events.on_tag(
                {"device": self.name, "epc": epc, "tid": None, "ant": 1, "rssi": None}
            )
