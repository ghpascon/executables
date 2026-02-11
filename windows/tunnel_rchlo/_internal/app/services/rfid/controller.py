import logging
from smartx_rfid.devices import DeviceManager
from smartx_rfid.utils import TagList
import asyncio
from smartx_rfid.utils import delayed_function


class Controller:
	def __init__(self, devices: DeviceManager, tags: TagList):
		self.box_info: dict = {}
		self.tags = tags
		self.devices = devices

	# [BOX INFO]
	def update_box_info(self, box_info: str):
		parts = box_info.split(';')
		box_id = None
		qty = 0
		if len(parts) == 1:
			box_id = parts[0]
		elif len(parts) == 2:
			box_id, qty_str = parts
			try:
				qty = int(qty_str)
			except ValueError:
				logging.warning(f"Invalid quantity '{qty_str}' in box info: {box_info}")
		self.box_info = {'box_id': box_id, 'qty': qty}
		logging.info(f'Updating box info: {self.box_info}')

	def validate_box_info(self, name: str):
		status = True
		if self.box_info.get('box_id') is None:
			logging.warning('Box info is missing box_id')
			status = False
		if self.box_info.get('qty', 0) <= 0:
			logging.warning('Box info has invalid quantity')
			status = False

		if not status:
			self.reject_box(name)
		return status

	# [ACTIONS]
	def approve_box(self, name: str):
		asyncio.create_task(self._approve(name))

	def reject_box(self, name: str):
		asyncio.create_task(self._reject(name))

	async def _approve(self, name: str):
		logging.info(f"{'='*20} Approving box {'='*20}")
		logging.info(f'Box info: {self.box_info}')
		success, msg = await self.devices.write_gpo(
			device_name=name, pin=1, state=True, control='pulsed', time=300
		)
		if not success:
			logging.error(f'Failed to write GPO for approving box: {msg}')
		else:
			logging.info('GPO write successful for approving box')
		self.reset_box()

	async def _reject(self, name: str):
		logging.info(f"{'='*20} Rejecting box {'='*20}")
		logging.info(f'Box info: {self.box_info}')
		success, msg = await self.devices.write_gpo(
			device_name=name, pin=2, state=True, control='pulsed', time=300
		)
		if not success:
			logging.error(f'Failed to write GPO for rejecting box: {msg}')
		else:
			logging.info('GPO write successful for rejecting box')
		self.reset_box()

	def reset_box(self):
		self.box_info = {}

	# [VALIDATION]
	def _validate(self):
		current_qty = len(self.tags)
		expected_qty = self.box_info.get('qty', 0)
		if current_qty < expected_qty:
			return 0
		elif current_qty > expected_qty:
			return 2
		else:
			return 1

	def validate_tags(self, name: str, make_action: bool = False):
		if not self.validate_box_info(name):
			return
		# Check if tag count matches box quantity
		if make_action:
			logging.info(f"{'='*20} Validating box {'='*20}")
		logging.info(f"Current qty: {len(self.tags)}, Expected qty: {self.box_info.get('qty', 0)}")
		state = self._validate()

		# Reading is still in progress, wait and re-validate
		if state == 0:
			if make_action:
				self.reject_box(name)
		# Box OK
		elif state == 1:
			if make_action:
				self.approve_box(name)
			else:
				asyncio.create_task(
					delayed_function(self.validate_tags, 1.0, name, make_action=True)
				)
		# Box NOK
		elif state == 2:
			self.reject_box(name)
