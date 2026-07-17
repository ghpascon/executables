import asyncio
import logging
import time

import serial.tools.list_ports
import serial_asyncio

from app.services.events import events

from .on_receive import OnReceive
from .rfid import RfidCommands


class ICARD(asyncio.Protocol, OnReceive, RfidCommands):
    def __init__(self, config, name):
        self.is_rfid_reader = True

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

        self.is_connected = False
        self.is_reading = False

        self.is_auto = self.port == "AUTO"

        self.step = 0
        self.session = self.config.get("SESSION", 1)

        # POWER
        self.power = self.config.get("POWER", 26)
        if self.power > 26:
            self.power = 26
        if self.power < 10:
            self.power = 10

    def connection_made(self, transport):
        self.transport = transport
        logging.info("✅ Serial connection successfully established.")
        asyncio.create_task(self.loop())

    def data_received(self, data):
        now = time.time()
        self.rx_buffer += data
        self.last_byte_time = now

        # Cancela tarefa anterior de timeout
        if hasattr(self, "_timeout_task") and self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()

        # Cria uma nova tarefa de timeout dentro da própria função
        async def timeout_clear():
            await asyncio.sleep(0.3)  # 300 ms
            # Se não chegou mais bytes, limpa o buffer
            if self.last_byte_time and (time.time() - self.last_byte_time) >= 0.3:
                if self.rx_buffer:
                    self.rx_buffer.clear()
                    logging.warning("⚠️ Buffer cleared due to 300ms timeout without receiving data.")

        self._timeout_task = asyncio.create_task(timeout_clear())

        # Processa pacotes completos
        while len(self.rx_buffer) > 0:
            packet_length = self.rx_buffer[0]  # primeiro byte = tamanho do pacote
            if len(self.rx_buffer) >= packet_length + 1:
                packet = self.rx_buffer[0 : packet_length + 1]
                asyncio.create_task(self.on_receive(packet))
                # Remove pacote do buffer
                self.rx_buffer = self.rx_buffer[packet_length + 1 :]
            else:
                # Pacote incompleto, espera por mais bytes
                break

    def connection_lost(self, exc):
        logging.error("⚠️ Serial connection lost.")
        self.transport = None
        self.is_connected = False
        asyncio.create_task(events.on_disconnect(self.name))
        self.is_reading = False
        self.step = 0

        if self.on_con_lost:
            self.on_con_lost.set()

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
