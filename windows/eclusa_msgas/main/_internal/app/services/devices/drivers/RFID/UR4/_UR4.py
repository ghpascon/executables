import asyncio
import logging

from app.services.events import events

from .helpers import ReaderHelpers
from .on_event import OnEvent
from .setup_reader import SetupReader
from .write_commands import WriteCommands


class UR4(ReaderHelpers, OnEvent, SetupReader, WriteCommands):
    def __init__(self, config, name):
        self.is_rfid_reader = True

        self.config = config
        self.device_name = name

        self.ip = self.config.get("CONNECTION")
        self.port = self.config.get("PORT", 8888)

        self.reader = None
        self.writer = None

        self.tags_to_write = {}

        self.is_connected = False
        self.is_reading = False

        self.setup = False
        self.setup_step = 0
        self.wait_answer = False
        self.current_timeout_answer = 0
        self.timeout_answer = 500

        self.ant_qtd = 4
        self.min_power = 10
        self.max_power = 30

        self.temperature = 0

        self.gpi = {"1": False, "2": False}
        self.gpi_config = self.config.get("GPI")

    async def connect(self):
        while True:
            try:
                logging.info(f"Tentando conectar ao leitor em {self.ip}:{self.port}")
                self.reader, self.writer = await asyncio.wait_for(
                    asyncio.open_connection(self.ip, self.port), timeout=3
                )
                self.is_connected = True
                asyncio.create_task(events.on_connect(self.name))
                logging.info(f"✅ [CONECTADO] Conectado a {self.ip}:{self.port}")

                # Rode as tarefas de forma independente para monitorar desconexão
                tasks = [
                    asyncio.create_task(self.receive_data()),
                    asyncio.create_task(self.setup_reader()),
                    asyncio.create_task(self.monitor_connection()),
                    asyncio.create_task(self.get_temperature()),
                    asyncio.create_task(self.ensure_reading_command()),
                    asyncio.create_task(self.get_gpi_state()),
                    asyncio.create_task(self.prevent_gpi_error()),
                ]

                # Aguarde até que uma das tarefas termine (ex: desconexão)
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

                # Cancela todas as tarefas restantes
                for task in pending:
                    task.cancel()

                self.is_connected = False
                asyncio.create_task(events.on_disconnect(self.name))
                logging.info("Conexão perdida, tentando reconectar...")

            except Exception as e:
                self.is_connected = False
                asyncio.create_task(events.on_disconnect(self.name))
                logging.error(f"❌ Erro: {e}. Tentando reconectar em 3 segundos...")

            await asyncio.sleep(3)

    async def send_data(self, data, verbose=True):
        if self.is_connected and self.writer:
            try:
                data[-3] = await self.get_bcc(data)
                data = bytes(data)
                self.writer.write(data)
                await self.writer.drain()
                if verbose:
                    logging.info(f"[ENVIADO] {' '.join(f'{b:02x}' for b in data)}")
            except Exception as e:
                logging.error(f"[ERRO ENVIO] {e}")
                self.is_connected = False
                asyncio.create_task(events.on_disconnect(self.name))

    async def start_inventory(self, test_mode=False, verbose=True):
        if self.is_reading:
            return
        await self.send_data(
            [0xA5, 0x5A, 0x00, 0x0A, 0x82, 0x00, 0x00, 0x00, 0x0D, 0x0A], verbose=verbose
        )
        if test_mode:
            return
        self.is_reading = True
        await events.on_start(self.device_name)

    async def stop_inventory(self, test_mode=False, verbose=True):
        if not self.is_reading:
            return
        await self.send_data([0xA5, 0x5A, 0x00, 0x08, 0x8C, 0x00, 0x0D, 0x0A], verbose=verbose)
        await self.send_data(
            [0xA5, 0x5A, 0x00, 0x09, 0x8D, 0x01, 0x00, 0x0D, 0x0A], verbose=verbose
        )
        if test_mode:
            return
        self.is_reading = False
        await events.on_stop(self.device_name)

    async def write_gpo(self, state: bool | str = True, *args, **kwargs):
        # Normaliza o estado para 0/1
        state_value = 0x01 if state else 0x00

        await self.send_data(
            [
                0xA5,
                0x5A,
                0x00,
                0x0C,
                0xA1,
                0x09,
                0x00,
                0x00,
                state_value,
                0x00,
                0x0D,
                0x0A,
            ]
        )

    async def get_connected(self):
        await self.send_data([0xA5, 0x5A, 0x00, 0x08, 0x4E, 0x00, 0x0D, 0x0A])
