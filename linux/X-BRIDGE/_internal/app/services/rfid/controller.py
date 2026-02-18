"""
Docstring for app.services.rfid.controller
This module will be used for custom logic.
"""

from smartx_rfid.devices import DeviceManager
from smartx_rfid.utils import TagList
from .integration import Integration


class Controller:
	def __init__(self, devices: DeviceManager, tags: TagList, integration: Integration):
		self.box_info: dict = {}
		self.tags = tags
		self.devices = devices
		self.integration = integration

	def on_event(self, name: str, event_type: str, event_data):
		pass

	def on_start(self, device: str):
		pass

	def on_stop(self, device: str):
		pass

	def on_new_tag(self, tag: dict):
		pass

	def on_existing_tag(self, tag: dict):
		pass
