import json
import logging
import os

from .add_device import AddDevice
from .devices_commands import DevicesCommands
from .manage_devices import ManageDevices


class Devices(AddDevice, DevicesCommands, ManageDevices):
    """
    The Devices class manages device configurations,
    loading them from JSON files, and providing utility
    functions to handle device data.
    """

    def __init__(self):
        """
        Initialize the Devices manager.
        - Loads devices from the configuration folder.
        """
        self.devices = {}
        self.connect_task = None
        self.get_devices_from_config()

    def _generate_unique_name(self, base_name):
        """
        Generate a unique device name based on the given base name.
        If the name already exists, add an incrementing index.

        Args:
            base_name (str): Suggested name for the device.

        Returns:
            str: A unique device name.
        """
        base_name = base_name.upper()
        if base_name not in self.devices:
            return base_name

        index = 2
        new_name = f"{base_name}_{index}"
        while new_name in self.devices:
            index += 1
            new_name = f"{base_name}_{index}"
        return new_name

    def get_devices_from_config(self, devices_path="config/devices"):
        """
        Load devices from JSON configuration files in the given directory.
        If the directory does not exist, it will be created.

        Args:
            devices_path (str): Path to the directory containing device config files.
        """
        logging.info("DEVICES:")
        self.devices = {}

        try:
            # Create directory if it does not exist
            if not os.path.exists(devices_path):
                os.makedirs(devices_path)
                logging.info(f"📁 Directory created: {devices_path}")
        except Exception as e:
            logging.error(f"❌ Error checking/creating directory '{devices_path}': {e}")
            return

        # Iterate over JSON files in the directory
        for filename in os.listdir(devices_path):
            if filename.endswith(".json"):
                filepath = os.path.join(devices_path, filename)
                logging.info(f"📄 File: {filename}")
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    # If the device config is invalid, remove the file
                    if data.get("READER") is None:
                        os.remove(filepath)
                        continue
                    name = filename.replace(".json", "")
                    self.add_device(data, name)
                except json.JSONDecodeError as e:
                    logging.error(f"❌ JSON decode error: {e}")
                except Exception as e:
                    logging.error(f"❌ Error processing file '{filename}': {e}")

    async def get_device_types(self, path="config/examples/device_examples"):
        """
        List available device types from example JSON files.

        Args:
            path (str): Path to the folder containing example device configs.

        Returns:
            list | dict: List of device type names or error dictionary.
        """
        try:
            filenames = []
            for file in os.listdir(path):
                if file.endswith(".json"):
                    filenames.append(os.path.splitext(file)[0])
            return filenames
        except Exception as e:
            return {"error": str(e)}

    async def get_example_config(self, device, path="config/examples/device_examples"):
        """
        Load and return the content of an example device configuration.

        Args:
            device (str): The device type (filename without extension).
            path (str): Path to the folder containing example configs.

        Returns:
            dict: JSON content of the example config or an error message.
        """
        try:
            path += f"/{device}.json"
            with open(path, "r") as f:
                content = json.load(f)
                return content
        except Exception:
            return {"error": "Device not found"}


devices = Devices()
