import asyncio
import logging


class ReaderHelpers:
    async def monitor_connection(self):
        while self.is_connected:
            await asyncio.sleep(1)
            if self.writer.is_closing():
                self.is_connected = False
                logging.info("[DESCONECTADO] Socket fechado.")
                break

    async def receive_data(self):
        await asyncio.sleep(0.03)
        buffer = b""
        try:
            while True:
                data = await self.reader.read(1024)
                if not data:
                    raise ConnectionError("Conexão perdida")
                buffer += data

                # Processa pacotes completos com prefixo a5 5a e sufixo 0d 0a
                while True:
                    start = buffer.find(b"\xa5\x5a")
                    end = buffer.find(b"\x0d\x0a", start)
                    if start != -1 and end != -1 and end > start:
                        packet = buffer[start : end + 2]
                        buffer = buffer[end + 2 :]
                        await self.on_received_cmd(packet)
                    else:
                        break

        except Exception as e:
            self.is_connected = False
            logging.error(f"[ERRO RECEBIMENTO] {e}")

    async def get_temperature(self):
        while True:
            await asyncio.sleep(10)
            if not self.setup:
                continue
            await self.send_data([0xA5, 0x5A, 0x00, 0x08, 0x34, 0x00, 0x0D, 0x0A])

    async def decode_temperature(self, response_bytes):
        temperature = int(int((response_bytes[6] << 8) | response_bytes[7]) / 100)
        logging.info(f"TEMPERATURE: {temperature}")
        return temperature

    async def get_gpi_state(self):
        while True:
            await asyncio.sleep(0.2)
            if not self.setup:
                continue
            await self.send_data([0xA5, 0x5A, 0x00, 0x09, 0xA1, 0x0A, 0x00, 0x0D, 0x0A], False)

    async def prevent_gpi_error(self):
        while True:
            await asyncio.sleep(1)
            if self.is_reading:
                continue
            await self.start_inventory(True, False)
            await asyncio.sleep(0.3)
            await self.stop_inventory(True, False)

    async def ensure_reading_command(self):
        while True:
            await asyncio.sleep(1)
            if self.is_reading:
                await self.send_data(
                    [0xA5, 0x5A, 0x00, 0x0A, 0x82, 0x00, 0x00, 0x00, 0x0D, 0x0A], False
                )

                continue
            await self.send_data([0xA5, 0x5A, 0x00, 0x08, 0x8C, 0x00, 0x0D, 0x0A], False)
            await self.send_data([0xA5, 0x5A, 0x00, 0x09, 0x8D, 0x01, 0x00, 0x0D, 0x0A], False)

    async def get_tid_from_epc(self, epc):
        current_tags = list(self.tags)
        for tag in current_tags:
            if tag == epc:
                return self.tags.get(tag).get("tid")
        return None

    async def get_bcc(self, data):
        bcc = 0
        for byte in data[2:-3]:
            bcc ^= byte
        return bcc
