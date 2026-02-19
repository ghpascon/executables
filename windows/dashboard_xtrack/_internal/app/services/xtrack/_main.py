from app.models.xtrack import Locations, Objects, Movements
from app.db import setup_database

from smartx_rfid.api import ApiXtrack
import logging
from app.core import settings
from smartx_rfid.db import DatabaseManager
from datetime import datetime


class XtackManager:
	def __init__(self, url: str):
		self.api = ApiXtrack(url)
		self.db_manager: DatabaseManager | None = None
		self.load_database()

	def load_database(self):
		self.db_manager = None
		try:
			if settings.DATABASE_URL is not None:
				logging.info('Setting up Database Integration')
				self.db_manager: DatabaseManager = setup_database(
					database_url=settings.DATABASE_URL
				)
				return True
			else:
				logging.warning('DATABASE_URL not set. Skipping Database Integration setup.')
				return False
		except Exception as e:
			logging.error(f'Error setting up Database Integration: {e}')
			return False

	def save_locations(self, locations: list[dict]) -> tuple[bool, str]:
		if not self.db_manager:
			return False, 'Database manager not initialized.'

		if not locations:
			return True, 'No locations to process.'

		with self.db_manager.get_session() as session:
			try:
				# Normaliza IDs para int
				ids = [int(loc['ID']) for loc in locations]

				# Busca existentes (id + name)
				existing = (
					session.query(Locations.id, Locations.name).filter(Locations.id.in_(ids)).all()
				)

				# Mapeia para dict {id: name}
				existing_map = {row.id: row.name for row in existing}

				to_insert = []
				to_update = []

				for loc in locations:
					loc_id = int(loc['ID'])
					loc_name = loc.get('NAME')

					if loc_id not in existing_map:
						to_insert.append({'id': loc_id, 'name': loc_name})
					else:
						db_name = existing_map[loc_id]

						# evita update desnecessário por None vs ""
						if (db_name or '') != (loc_name or ''):
							to_update.append({'id': loc_id, 'name': loc_name})

				if to_insert:
					session.bulk_insert_mappings(Locations, to_insert)

				if to_update:
					session.bulk_update_mappings(Locations, to_update)

				session.commit()

				logging.info(
					f'Locations saved: {len(to_insert)} inserted, {len(to_update)} updated'
				)
				return True, f'{len(to_insert)} inserted, {len(to_update)} updated'

			except Exception as e:
				session.rollback()
				logging.error(f'Error saving locations: {e}')
				return False, str(e)

	def save_objects(self, objects: list[dict]) -> tuple[bool, str]:
		if not self.db_manager:
			return False, 'Database manager not initialized.'
		if not objects:
			return True, 'No objects to process.'

		def parse_dt(val):
			if not val:
				return None
			if isinstance(val, str):
				try:
					return datetime.fromisoformat(val)
				except Exception:
					return None
			return val

		def dt_equal(a, b):
			"""Compara datetimes ignorando microsegundos e tz"""
			if a is None and b is None:
				return True
			if a is None or b is None:
				return False
			return a.replace(tzinfo=None, microsecond=0) == b.replace(tzinfo=None, microsecond=0)

		with self.db_manager.get_session() as session:
			try:
				idcodes = [obj['IDCODE'] for obj in objects]

				# Busca existentes de uma vez
				existing = (
					session.query(
						Objects.idcode,
						Objects.last_modified,
						Objects.last_location,
						Objects.last_seen,
						Objects.location_id,
					)
					.filter(Objects.idcode.in_(idcodes))
					.all()
				)

				existing_map = {row.idcode: row for row in existing}

				to_insert, to_update, movements_to_insert = [], [], []

				for obj in objects:
					idcode = obj['IDCODE']
					new_data = {
						'idcode': idcode,
						'active': obj.get('ACTIVE') == '1',
						'location_id': int(obj['LOCATION_ID']) if obj.get('LOCATION_ID') else None,
						'description': obj.get('DESCRIPTION'),
						'last_seen': parse_dt(obj.get('LAST_SEEN')),
						'home_location_id': int(obj['HOME_LOCATION_ID'])
						if obj.get('HOME_LOCATION_ID')
						else None,
						'last_modified': parse_dt(obj.get('LAST_MODIFIED')),
						'last_location': parse_dt(obj.get('LAST_LOCATION')),
					}

					db_obj = existing_map.get(idcode)
					if not db_obj:
						to_insert.append(new_data)
					else:
						changed = False
						location_changed = db_obj.location_id != new_data['location_id']

						for field in ['last_modified', 'last_location', 'last_seen']:
							if not dt_equal(getattr(db_obj, field), new_data[field]):
								logging.info(
									f'UPDATE idcode={idcode} campo={field}: db={getattr(db_obj, field)} input={new_data[field]}'
								)
								changed = True
								break

						if changed:
							to_update.append(new_data)

							if location_changed:
								movements_to_insert.append(
									{
										'object_idcode': idcode,
										'from_location_id': db_obj.location_id,
										'to_location_id': new_data['location_id'],
										'timestamp': datetime.now(),
									}
								)

				if to_insert:
					session.bulk_insert_mappings(Objects, to_insert)
				if to_update:
					session.bulk_update_mappings(Objects, to_update)
				if movements_to_insert:
					session.bulk_insert_mappings(Movements, movements_to_insert)

				session.commit()
				logging.info(f'Objects saved: {len(to_insert)} inserted, {len(to_update)} updated')
				return True, f'{len(to_insert)} inserted, {len(to_update)} updated'

			except Exception as e:
				session.rollback()
				logging.error(f'Error saving objects: {e}')
				return False, str(e)

	def get_info(self):
		with self.db_manager.get_session() as session:
			try:
				locations_count = session.query(Locations).count()
				objects_count = session.query(Objects).count()
				objects_in_locations = {
					loc.name: session.query(Objects).filter(Objects.location_id == loc.id).count()
					for loc in session.query(Locations).all()
				}
				objects_in_locations = {k: v for k, v in objects_in_locations.items() if v > 0}
				movements_count = session.query(Movements).count()
				movements_today = (
					session.query(Movements)
					.filter(
						Movements.created_at
						>= datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
					)
					.count()
				)
				# Movimentos de hoje por local (entradas e saídas)
				today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
				movements_entries_today = {
					loc.name: session.query(Movements)
					.filter(Movements.to_location_id == loc.id, Movements.created_at >= today)
					.count()
					for loc in session.query(Locations).all()
				}
				movements_entries_today = {
					k: v for k, v in movements_entries_today.items() if v > 0
				}

				movements_exits_today = {
					loc.name: session.query(Movements)
					.filter(Movements.from_location_id == loc.id, Movements.created_at >= today)
					.count()
					for loc in session.query(Locations).all()
				}
				movements_exits_today = {k: v for k, v in movements_exits_today.items() if v > 0}
				return True, {
					'xtrack_url': self.api.base_url,
					'locations_count': locations_count,
					'objects_count': objects_count,
					'objects_in_locations': objects_in_locations,
					'movements_count': movements_count,
					'movements_today': movements_today,
					'movements_entries_today': movements_entries_today,
					'movements_exits_today': movements_exits_today,
				}
			except Exception as e:
				logging.error(f'Error getting Xtrack info: {e}')
				return False, str(e)
