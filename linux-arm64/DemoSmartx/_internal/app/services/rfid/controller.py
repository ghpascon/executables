"""
Docstring for app.services.rfid.controller
This module will be used for custom logic.
"""

from smartx_rfid.devices import DeviceManager
from smartx_rfid.utils import TagList
from .integration import Integration
import logging
from app.models.controller import Orders, FinishedOrders
import ast


class Controller:
	def __init__(self, devices: DeviceManager, tags: TagList, integration: Integration):
		self.box_info: dict = {}
		self.tags = tags
		self.devices = devices
		self.integration: Integration = integration
		self.order_data: dict = {}

	# [ EVENTS ]
	def on_event(self, name: str, event_type: str, event_data):
		pass
		# asyncio.create_task(
		# 	self.integration.on_event_integration(
		# 		name=name, event_type=event_type, event_data=event_data
		# 	)
		# )

	# [ Reading Events ]
	def on_start(self, device: str):
		pass

	def on_stop(self, device: str):
		pass

	# [ Tag Events ]
	def on_new_tag(self, tag: dict):
		# asyncio.create_task(self.integration.on_tag_integration(tag=tag))
		pass

	def on_existing_tag(self, tag: dict):
		pass

	# [ Conference ]
	def add_orders(self, orders: list):
		# Accepts: list of dicts with 'order', 'epc', 'description' (single or list)
		if not isinstance(orders, list):
			orders = [orders]
		# Group tags by order
		grouped = {}
		for item in orders:
			order_id = item['order']
			tag = {'epc': item['epc'], 'description': item['description']}
			if order_id not in grouped:
				grouped[order_id] = []
			grouped[order_id].append(tag)
		try:
			for order_id, tags in grouped.items():
				with self.integration.db_manager.get_session() as session:
					existing_order = session.query(Orders).filter_by(order=order_id).first()
					if existing_order:
						try:
							existing_tags = ast.literal_eval(existing_order.tags)
						except Exception:
							existing_tags = []
						existing_epcs = {
							tag['epc']
							for tag in existing_tags
							if isinstance(tag, dict) and 'epc' in tag
						}
						new_tags = 0
						for tag in tags:
							epc = tag.get('epc')
							if epc and epc not in existing_epcs:
								existing_tags.append(tag)
								existing_epcs.add(epc)
								new_tags += 1
						existing_order.tags = str(existing_tags)
						session.commit()
						logging.info(f"Order '{order_id}' updated: {new_tags} new tag(s) added.")
					else:
						new_order = Orders(order=order_id, tags=str(tags))
						session.add(new_order)
						session.commit()
						logging.info(f"Order '{order_id}' created with {len(tags)} tag(s).")
			logging.info('All orders processed successfully.')
			return True, 'Orders added successfully.'
		except Exception as e:
			logging.error(f'Failed to add orders: {e}')
			return False, f'Error adding orders: {e}'

	def get_orders(self):
		with self.integration.db_manager.get_session() as session:
			orders = session.query(Orders).all()
			return [{'order': o.order, 'tags': self._parse_tags(o.tags)} for o in orders]

	def set_order(self, order_data: dict):
		self.order_data = order_data
		self.tags.clear()  # Clear current tags to start fresh for the new order

	def get_order(self, order_id: str):
		with self.integration.db_manager.get_session() as session:
			order = session.query(Orders).filter_by(order=order_id).first()
			if order:
				return {'order': order.order, 'tags': self._parse_tags(order.tags)}
			else:
				return None

	@staticmethod
	def _parse_tags(tags_str):
		try:
			return ast.literal_eval(tags_str)
		except Exception:
			return []

	def get_comparison(self):
		read_tags = self.tags.get_epcs()
		expected_tags = self.order_data.get('tags', [])
		for expected in expected_tags:
			expected['found'] = expected['epc'] in read_tags
			if expected['found']:
				read_tags.pop(read_tags.index(expected['epc']))
		return {'tags': expected_tags, 'unexpected': read_tags}

	def finish_order(self):
		comparison = self.get_comparison()
		if len(comparison['unexpected']) > 0:
			return (
				False,
				f"Cannot finish order: {len(comparison['unexpected'])} unexpected tag(s) found.",
			)
		if any(not tag['found'] for tag in comparison['tags']):
			return False, 'Cannot finish order: Some expected tags were not found.'
		with self.integration.db_manager.get_session() as session:
			order = session.query(Orders).filter_by(order=self.order_data.get('order')).first()
			if order:
				finished_order = FinishedOrders(order=order.order, tags=order.tags, success=True)
				session.add(finished_order)
				session.delete(order)
				session.commit()
				self.order_data = {}
				self.tags.clear()
				return True, 'Order finished successfully.'
			else:
				return False, 'Order not found in database.'
