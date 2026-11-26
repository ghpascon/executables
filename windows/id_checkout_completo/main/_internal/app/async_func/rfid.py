from app.services import rfid_manager
import logging
import asyncio
from app.core import settings
from datetime import datetime, timedelta
from app.models import get_all_models


async def connect_on_startup():
	"""Connect to RFID devices on application startup."""
	logging.info('Connecting to RFID devices on startup...')

	# Attempt initial connect once, then monitor the connection tasks. If all
	# tasks finish (e.g., due to errors), attempt reconnect with a small backoff.
	try:
		await rfid_manager.devices.connect_devices()
	except Exception as e:
		logging.error(f'Error during initial devices.connect_devices(): {e}')

	backoff_seconds = 1
	while True:
		# get current connect tasks
		tasks = getattr(rfid_manager.devices, '_connect_tasks', []) or []
		# If there are no tasks or all are done, attempt to reconnect after backoff
		if not tasks or all(t.done() for t in tasks):
			await asyncio.sleep(backoff_seconds)
			try:
				await rfid_manager.devices.connect_devices()
			except Exception as e:
				logging.error(f'Error reconnecting devices: {e}')
				# increase backoff up to a limit to avoid tight restart loops
				backoff_seconds = min(backoff_seconds * 2, 60)
				continue
			# reset backoff on successful start
			backoff_seconds = 1
		else:
			# tasks are running; check again later
			await asyncio.sleep(1)


async def clear_old_tags():
	while True:
		if settings.CLEAR_OLD_TAGS_INTERVAL is None or settings.CLEAR_OLD_TAGS_INTERVAL <= 0:
			await asyncio.sleep(600)
			continue
		await asyncio.sleep(
			1 if settings.CLEAR_OLD_TAGS_INTERVAL < 10 else settings.CLEAR_OLD_TAGS_INTERVAL / 2
		)
		if len(rfid_manager.tags) == 0:
			continue

		timestamp = datetime.now() - timedelta(seconds=settings.CLEAR_OLD_TAGS_INTERVAL)
		removed_tags = rfid_manager.tags.remove_tags_before_timestamp(timestamp)
		if removed_tags:
			logging.info(f'Removed {len(removed_tags)} old tags: {removed_tags}')
			for tag in removed_tags:
				rfid_manager.on_event(
					device=rfid_manager.build_device(
						name=tag.get('device', 'unknown'),
						serial_number=tag.get('device_serial_number'),
					),
					event_type='tag_removed',
					event_data=tag,
				)


async def clear_db():
	"""Clear database at startup and daily at midnight."""
	seconds_until_midnight = 0
	while True:
		# Sleep until midnight
		await asyncio.sleep(seconds_until_midnight)
		# Calculate initial seconds until midnight
		now = datetime.now()
		tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
		seconds_until_midnight = (tomorrow - now).total_seconds()

		logging.info('CLEAR DATABASE')

		# Validation
		if not isinstance(settings.STORAGE_DAYS, int):
			logging.warning('Invalid STORAGE_DAYS setting. Skipping database cleanup.')
			await asyncio.sleep(seconds_until_midnight)
			continue

		if rfid_manager.integration.db_manager is None:
			logging.warning('Database manager is not initialized. Skipping database cleanup.')
			await asyncio.sleep(seconds_until_midnight)
			continue

		logging.info(f'Clearing database entries older than {settings.STORAGE_DAYS} days.')

		# Calculate cutoff timestamp
		cutoff_date = datetime.now() - timedelta(days=settings.STORAGE_DAYS)

		# Get all models
		models = get_all_models()

		with rfid_manager.integration.db_manager.get_session() as session:
			for model in models:
				if not getattr(model, '__cleanup__', False):
					logging.info(
						f"Model {model.__tablename__} does not have '__cleanup__' set to True. Skipping."
					)
					continue
				# Determine which timestamp column to use (prefer updated_at, fallback to created_at)
				timestamp_column = None
				if hasattr(model, 'created_at'):
					timestamp_column = model.created_at
				elif hasattr(model, 'updated_at'):
					timestamp_column = model.updated_at
				else:
					logging.info(
						f"Model {model.__tablename__} does not have 'updated_at' or 'created_at' column. Skipping."
					)
					continue

				try:
					# Delete old records
					deleted_count = (
						session.query(model).filter(timestamp_column < cutoff_date).delete()
					)
					session.commit()

					if deleted_count > 0:
						logging.info(
							f'Deleted {deleted_count} old records from {model.__tablename__}'
						)
					else:
						logging.info(f'No old records to delete from {model.__tablename__}')

				except Exception as e:
					logging.error(f'Error clearing {model.__tablename__}: {e}')
					session.rollback()

		logging.info('Database cleanup completed.')


async def update_today_count():
	"""Update the count for today."""
	while True:
		try:
			data = rfid_manager.controller.get_today_count()
			if isinstance(data, list):
				data = data[0] if data else {'total': 0}
			if isinstance(data, dict):
				rfid_manager.controller.today_count = data.get('total', 0)
		except Exception as e:
			logging.error(f'Error updating today count: {e}')
		await asyncio.sleep(60)  # Update every minute
