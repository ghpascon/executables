import asyncio
from .on_receive import OnReceive
from .rfid import RfidCommands
from .serial_protocol import SerialProtocol
from .ble_protocol import BLEProtocol

class X714(SerialProtocol, OnReceive, RfidCommands, BLEProtocol):
    def __init__(self, config, name):
        self.is_rfid_reader = True

        self.name = name
        self.config = config

        self.is_bluetooth = self.config.get("IS_BLUETOOTH", False)
        self.ble_name = self.config.get("BLE_NAME", "XPAD_PLUS")
        self.init_ble_vars()

        self.port = self.config.get("CONNECTION", "AUTO")
        self.baudrate = self.config.get("BAUDRATE", 115200)
        self.vid = self.config.get("VID", 1)
        self.pid = self.config.get("PID", 1)

        self.transport = None
        self.on_con_lost = None
        self.rx_buffer = bytearray()
        self.last_byte_time = None

        self.is_connected = False
        self.is_reading = False

        self.is_auto = self.port == "AUTO"


    def write(self, to_send, verbose=True):
        if self.is_bluetooth:
            asyncio.run(self.write_ble(to_send.encode(), verbose))
        else:
            self.write_serial(to_send, verbose)

    async def connect(self):
        if self.is_bluetooth:
            await self.connect_ble()
        else:
            await self.connect_serial()
