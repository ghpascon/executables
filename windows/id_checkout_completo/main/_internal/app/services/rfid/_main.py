import logging
from smartx_rfid.devices import DeviceManager
from smartx_rfid.utils import TagList
from smartx_rfid.utils.event import normalize_device
from .integration import Integration
from app.core import settings
from .controller import Controller


class RfidManager:
	def __init__(self, devices_path: str, example_path: str = ''):
		logging.info('Initializing RfidManager')

		# TAGS
		self.tags = TagList(unique_identifier='tid', prefix=settings.TAG_PREFIX)

		# connect to devices
		self.devices = DeviceManager(
			devices_path=devices_path, example_path=example_path, event_func=self.on_event
		)

		# INTEGRATION
		self.integration = Integration()

		# CONTROLLER
		self.controller = Controller(
			devices=self.devices, tags=self.tags, integration=self.integration
		)

		logging.info(f"{'='*20} RfidManager initialized {'='*20}")

	# ===== DEVICE HELPERS =====
	def build_device(self, name: str, serial_number: str | None = None) -> dict:
		"""
		Build the device descriptor sent along with every event.

		When no serial number is provided, it is resolved from the connected
		device registered under ``name`` (if any).

		Args:
		    name: Device name.
		    serial_number: Optional device serial number.

		Returns:
		    dict: ``{'name': str, 'serial_number': str | None}``
		"""
		if serial_number is None:
			success, resolved = self.devices.get_serial_number(name)
			serial_number = resolved if success else None
		return {'name': name, 'serial_number': serial_number}

	# ===== R700 =====
	def handle_r700_event(self, events: list):
		for event in events:
			event_type = event.get('eventType')
			device = self.build_device(event.get('hostname', 'unknown'))
			if event_type == 'tagInventory':
				tag_data = event.get('tagInventoryEvent')
				if tag_data is not None:
					current_tag = {
						'epc': tag_data.get('epcHex'),
						'tid': tag_data.get('tidHex'),
						'ant': tag_data.get('antennaPort'),
						'rssi': int(tag_data.get('peakRssiCdbm', 0) / 100),
					}
					self.on_tag(device=device, tag_data=current_tag)
			elif event_type == 'inventoryStatus':
				event_data = event.get('inventoryStatusEvent')
				if event_data is not None:
					self.on_event(
						device=device,
						event_type='reading',
						event_data=event_data.get('inventoryStatus') == 'running',
					)

	# ===== EVENTS =====
	def on_event(self, device: dict | str, event_type: str, event_data=None):
		"""
		Entry point for every device event.

		Args:
		    device: Device descriptor ``{'name': ..., 'serial_number': ...}``
		        (a plain string is treated as the device name).
		    event_type: Event type (e.g. ``tag``, ``reading``, ``connection``).
		    event_data: Event payload.
		"""
		device = normalize_device(device)
		if event_type == 'tag':
			self.on_tag(device=device, tag_data=event_data)
		else:
			if event_type == 'reading':
				self.controller.on_start(device=device) if event_data else self.controller.on_stop(
					device=device
				)

			self.controller.on_event(device=device, event_type=event_type, event_data=event_data)

	def on_tag(self, device: dict | str, tag_data: dict):
		device = normalize_device(device)
		new_tag, tag = self.tags.add(tag_data, device=device)

		# NEW TAG
		if new_tag:
			self.controller.on_new_tag(device=device, tag=tag)

		# EXISTING TAG
		elif tag is not None:
			self.controller.on_existing_tag(device=device, tag=tag)
		return new_tag, tag

	# [ X-SCAN]
	def on_xscan_event(
		self,
		device_name: str,
		event_type: str,
		event_data,
		device_serial_number: str | None = None,
	):
		# inventory event with tags
		logging.info(
			f'Received X-SCAN event from device {device_name}: {event_type} - {event_data}'
		)
		device = self.build_device(device_name, device_serial_number)
		if event_type == 'inventory':
			for tag in event_data.get('tags', []):
				new_tag, tag_data = self.on_tag(
					device=device,
					tag_data={
						'epc': tag.get('epc'),
						'tid': tag.get('tid'),
						'ant': tag.get('antenna', 1),
						'rssi': tag.get('rssi'),
					},
				)
				if tag_data:
					tag_data['count'] += (
						tag.get('read_count', 1) - 1
					)  # Adjust count based on read_count
		else:
			self.on_event(device=device, event_type=event_type, event_data=event_data)
