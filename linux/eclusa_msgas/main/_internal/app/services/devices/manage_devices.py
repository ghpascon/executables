import asyncio
import json
import logging
import os


class ManageDevices:
    def __init__(self):
        self.devices = {}
        self.connect_task = None

    def ensure_devices_path(self, path):
        try:
            if not os.path.exists(path):
                os.makedirs(path)
                logging.info(f"📁 Diretório criado: {path}")
        except Exception as e:
            logging.error(f"❌ Erro ao criar/verificar diretório '{path}': {e}")
            raise

    async def connect_loop(self):
        tasks = []
        for name, device in self.devices.items():
            try:
                logging.info(f"🚀 Iniciando conexão para '{name}'")
                task = asyncio.create_task(device.connect())
                tasks.append(task)
            except Exception as e:
                logging.error(f"❌ Erro ao iniciar conexão para '{name}': {e}")
        await asyncio.gather(*tasks)

    async def create_connect_loop(self):
        self.connect_task = asyncio.create_task(self.connect_loop())

    async def restart_connect_loop(self):
        if self.connect_task and not self.connect_task.done():
            self.connect_task.cancel()
            try:
                await self.connect_task
            except asyncio.CancelledError:
                logging.info("🔁 Loop de conexão anterior cancelado.")
        await self.create_connect_loop()

    async def create_device(self, data, name="default", path="config/devices"):
        self.ensure_devices_path(path)
        name = self._generate_unique_name(name)
        filename = f"{path}/{name}.json"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self.get_devices_from_config()
            await self.restart_connect_loop()
            return {"msg": f"{name} created"}
        except Exception as e:
            logging.error("❌ Erro ao criar o dispositivo:", e)
            return {"error": str(e)}

    async def update_device(self, data, name="default", path="config/devices"):
        self.ensure_devices_path(path)
        name = name.upper()
        filename = f"{path}/{name}.json"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            self.get_devices_from_config()
            await self.restart_connect_loop()
            return {"msg": f"{name} updated"}
        except Exception as e:
            logging.error("❌ Erro ao atualizar o dispositivo:", e)
            return {"error": str(e)}

    async def delete_device(self, name="default", path="config/devices"):
        self.ensure_devices_path(path)
        name = name.upper()
        filename = f"{path}/{name}.json"

        try:
            if os.path.exists(filename):
                os.remove(filename)
                logging.info(f"🗑️ Arquivo '{filename}' removido.")
            else:
                return {"error": f"Dispositivo '{name}' não encontrado."}

            self.get_devices_from_config()
            await self.restart_connect_loop()
            return {"msg": f"{name} deleted"}

        except Exception as e:
            logging.error("❌ Erro ao deletar o dispositivo:", e)
            return {"error": str(e)}
