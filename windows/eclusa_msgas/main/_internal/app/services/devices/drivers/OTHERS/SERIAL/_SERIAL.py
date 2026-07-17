import asyncio
import logging
import time

import serial.tools.list_ports
import serial_asyncio

from app.schemas.events import events

from .on_receive import OnReceive


class SERIAL(asyncio.Protocol, OnReceive):
    def __init__(self, config, name):
        self.is_rfid_reader = False

        self.config = config
        self.port = self.config.get("CONNECTION")
        self.baudrate = self.config.get("BAUDRATE")
        self.vid = self.config.get("VID", 1)
        self.pid = self.config.get("PID", 1)
        self.name = name

        self.transport = None
        self.on_con_lost = None
        self.rx_buffer = bytearray()
        self.last_byte_time = None
        self.is_auto = self.port == "AUTO"

        self.event_type = self.config.get("EVENT_TYPE", "generic")
        self.is_connected = False
        self.is_reading = False

    def connection_made(self, transport):
        self.transport = transport
        logging.info("✅ Serial connection successfully established.")
        self.is_connected = True
        asyncio.create_task(events.on_connect(self.name))

    def data_received(self, data):
        now = time.time()
        self.rx_buffer += data
        self.last_byte_time = now

        # Cancela tarefa anterior de timeout
        if hasattr(self, "_timeout_task") and self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()

        # Cria nova tarefa de timeout
        async def timeout_clear():
            await asyncio.sleep(0.3)  # 300 ms
            if self.last_byte_time and (time.time() - self.last_byte_time) >= 0.3:
                if self.rx_buffer:
                    self.rx_buffer.clear()
                    logging.warning("⚠️ Buffer cleared due to 300ms timeout without receiving data.")

        self._timeout_task = asyncio.create_task(timeout_clear())

        # Processa mensagens completas
        while b"\n" in self.rx_buffer or b"\r" in self.rx_buffer:
            # Encontra posição do primeiro delimitador
            positions = [
                p for p in [self.rx_buffer.find(b"\n"), self.rx_buffer.find(b"\r")] if p != -1
            ]
            pos = min(positions)

            # Extrai mensagem em bytes e converte para string
            message_bytes = self.rx_buffer[:pos]
            message = message_bytes.decode(errors="ignore").strip("\r\n")

            # Remove mensagem do buffer
            self.rx_buffer = self.rx_buffer[pos + 1 :]

            if message:
                asyncio.create_task(self.on_receive(message))

    def connection_lost(self, exc):
        logging.error("⚠️ Serial connection lost.")
        self.transport = None
        self.is_connected = False
        self.step = 0

        if self.on_con_lost:
            self.on_con_lost.set()
        asyncio.create_task(events.on_disconnect(self.name))

    def write(self, to_send, verbose=True):
        if self.transport:
            if isinstance(to_send, str):
                to_send += "\n"
                to_send = to_send.encode()

            # If it's bytes, calculate CRC and replace last two bytes
            if isinstance(to_send, bytes) and len(to_send) >= 2:
                crc = self.crc16(to_send)
                to_send = to_send[:-2] + bytes([crc & 0xFF, crc >> 8])

            if verbose:
                if isinstance(to_send, bytes):
                    hex_list = [f"0x{b:02X}" for b in to_send]
                    logging.info(f"📤 Sending: {hex_list}")
                else:
                    logging.info(f"📤 Sending: {to_send}")

            self.transport.write(to_send)
        else:
            logging.error("❌ Send attempt failed: connection not established.")

    async def connect(self):
        """Serial connection/reconnection loop"""
        loop = asyncio.get_running_loop()

        while True:
            self.on_con_lost = asyncio.Event()

            # If AUTO mode, try to detect port by VID/PID
            if self.is_auto:
                logging.info("🔍 Auto-detecting port")
                ports = serial.tools.list_ports.comports()
                found_port = None
                for p in ports:
                    # p.vid and p.pid are integers (e.g. 0x0001 == 1 decimal)
                    if p.vid == self.vid and p.pid == self.pid:
                        found_port = p.device
                        logging.info(f"✅ Detected port: {found_port}")
                        break

                if found_port is None:
                    logging.warning(f"⚠️ No port with VID={self.vid} and PID={self.pid} found.")
                    logging.info("⏳ Retrying in 3 seconds...")
                    await asyncio.sleep(3)
                    continue  # try to detect again in next loop
                else:
                    self.port = found_port

            try:
                logging.info(f"🔌 Trying to connect to {self.port} at {self.baudrate} bps...")
                await serial_asyncio.create_serial_connection(
                    loop, lambda: self, self.port, baudrate=self.baudrate
                )
                logging.info("🟢 Successfully connected.")
                await self.on_con_lost.wait()
                logging.info("🔄 Connection lost. Attempting to reconnect...")
            except Exception as e:
                logging.error(f"❌ Connection error: {e}")

            # If in AUTO mode, reset port to "AUTO" to force detection next loop
            if self.is_auto:
                self.port = "AUTO"

            logging.info("⏳ Waiting 3 seconds before retrying...")
            await asyncio.sleep(3)

    def crc16(self, data: bytes, poly=0x8408):
        """CRC-16/CCITT-FALSE calculation (poly=0x8408)"""
        crc = 0xFFFF
        for byte in data[:-2]:  # exclude last two bytes (CRC placeholder)
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ poly
                else:
                    crc >>= 1
        return crc & 0xFFFF
