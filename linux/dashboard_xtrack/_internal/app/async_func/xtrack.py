import logging
import asyncio
from app.services.xtrack import xtrack_manager
from datetime import datetime

UPDATE_TIME = 300


def update_tables():
	asyncio.create_task(get_locations(False))
	asyncio.create_task(get_objects(False))


async def get_locations(loop=True):
	while True:
		logging.info('Fetching locations from Xtrack...')
		start_time = datetime.now()
		success, response = await xtrack_manager.api.get_locations()
		api_time = datetime.now()
		if success:
			logging.info(f'Locations fetched successfully: {len(response)} locations')
			logging.info(response[0])
			await asyncio.to_thread(xtrack_manager.save_locations, response)
			save_time = datetime.now()
			logging.info(f"{'='*30} Locations {'='*30}")
			logging.info(f'Time taken: API: {api_time - start_time}, Save: {save_time - api_time}')
		else:
			logging.error(f'Failed to fetch locations: {response}')

		if not loop:
			break
		await asyncio.sleep(UPDATE_TIME)


async def get_objects(loop=True):
	while True:
		logging.info('Fetching objects from Xtrack...')
		start_time = datetime.now()
		success, response = await xtrack_manager.api.get_objects()
		api_time = datetime.now()
		if success:
			logging.info(f'Objects fetched successfully: {len(response)} objects')
			logging.info(response[0])
			await asyncio.to_thread(xtrack_manager.save_objects, response)
			save_time = datetime.now()
			logging.info(f"{'='*30} Objects {'='*30}")
			logging.info(f'Time taken: API: {api_time - start_time}, Save: {save_time - api_time}')
		else:
			logging.error(f'Failed to fetch objects: {response}')

		if not loop:
			break
		await asyncio.sleep(UPDATE_TIME)
