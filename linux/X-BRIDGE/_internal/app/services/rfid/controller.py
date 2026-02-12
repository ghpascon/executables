"""
Docstring for app.services.rfid.controller
This module will be used for custom logic.
"""

from smartx_rfid.devices import DeviceManager
from smartx_rfid.utils import TagList


class Controller:
	def __init__(self, devices: DeviceManager, tags: TagList):
		self.box_info: dict = {}
		self.tags = tags
		self.devices = devices
