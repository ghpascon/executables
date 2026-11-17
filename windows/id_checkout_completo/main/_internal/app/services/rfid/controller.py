"""
Docstring for app.services.rfid.controller
This module will be used for custom logic.
"""

from smartx_rfid.devices import DeviceManager
from smartx_rfid.utils import TagList
from smartx_rfid.dispatcher import EventDispatcher
from app.core import DISPATCHER_PATH, EXAMPLES_DISPATCHER_PATH
from .integration import Integration
import asyncio
from app.core import settings
import logging
from smartx_rfid.schemas.tag import WriteTagValidator
from smartx_rfid.db import DatabaseManager
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pyepc import SGTIN


def _system_device(name: str) -> dict:
	"""Device descriptor for events that do not originate from a physical device."""
	return {'name': name, 'serial_number': None}


@dataclass
class SupportData:
	support: str
	data: list


class Controller:
	def __init__(self, devices: DeviceManager, tags: TagList, integration: Integration):
		self.tags = tags
		self.devices = devices
		self.integration = integration
		self.dispatcher = EventDispatcher(
			dispatches_path=DISPATCHER_PATH,
			example_path=EXAMPLES_DISPATCHER_PATH,
		)
		self.write_list: dict = {}
		self.as_400: DatabaseManager | None = None
		self.db_user = settings.DB_USER
		self.db_password = settings.DB_PASSWORD
		self.setup_as_400()

		self.operation: str = ''
		self.today_count: int | None = None
		self.support_data: SupportData | None = None
		self.last_serial_gtin = 0
		self._single_saved_tags: set[str] = set()

	# [ EVENTS ]
	def on_event(self, device: dict, event_type: str, event_data):
		"""
		Handle a generic event.

		Args:
		    device: Device descriptor ``{'name': ..., 'serial_number': ...}``.
		    event_type: Event type.
		    event_data: Event payload.
		"""
		logging.info(
			f"[ EVENT ] {device.get('name')} (SN: {device.get('serial_number')}) - "
			f'{event_type}: {event_data}'
		)
		# if not license_manager.validate_license():
		# 	return
		asyncio.create_task(
			self.integration.on_event_integration(
				device=device, event_type=event_type, event_data=event_data
			)
		)
		asyncio.create_task(
			self.dispatcher.add_async(device=device, event_type=event_type, data=event_data)
		)

	# [ Reading Events ]
	def on_start(self, device: dict):
		logging.info(f"[ START ] {device.get('name')}")
		# if not license_manager.validate_license():
		# 	return
		if settings.CLEAR_ON_START:
			self.tags.remove_tags_by_device(device=device)

	def on_stop(self, device: dict):
		logging.info(f"[ STOP ] {device.get('name')}")

	# [ Tag Events ]
	def on_new_tag(self, device: dict, tag: dict):
		logging.info(f"[ TAG ] {device.get('name')} - {tag}")
		self._persist_single_tag(tag)
		# if not license_manager.validate_license():
		# 	return
		asyncio.create_task(self.integration.on_tag_integration(tag=tag))
		asyncio.create_task(self.dispatcher.add_async(device=device, event_type='tag', data=tag))

	def on_existing_tag(self, device: dict, tag: dict):
		self._persist_single_tag(tag)
		asyncio.create_task(self.check_target(tag))
		if settings.ALWAYS_SEND:
			# if not license_manager.validate_license():
			# 	return
			asyncio.create_task(self.integration.on_tag_integration(tag=tag))
			asyncio.create_task(
				self.dispatcher.add_async(device=device, event_type='tag', data=tag)
			)

	def _persist_single_tag(self, tag: dict):
		if self.operation != 'single' or not self.support_data:
			return
		try:
			self._save_single_tag(tag)
		except Exception:
			logging.exception('Failed to save Single tag')

	# [ WRITE LIST ]
	def create_write_list_prefix(self, epcs: list, prefix: str):
		self.clear_write_list()
		for epc in epcs:
			target = f'{prefix}{epc[len(prefix):]}'
			current_tag = self.tags.get_by_identifier(epc)
			if current_tag:
				self.add_to_write_list(current_tag, target)
			else:
				logging.error(f'Epc: {epc} not in tags, skipping...')
		return self.write_list

	def add_to_write_list(self, tag: dict, target: str):
		self.write_list[tag.get('tid')] = {
			'target': target.lower(),
			'original_epc': tag.get('epc'),
		}
		tag['target'] = target
		logging.info(f"Added tag {tag.get('tid')} to write list with target {tag.get('target')}")
		self.on_event(
			device=_system_device('write_list'),
			event_type='add_to_write_list',
			event_data=tag,
		)

	def remove_from_write_list(self, tag: dict):
		tid = tag.get('tid')
		if tid in self.write_list:
			logging.info(f'Removed tag {tid} from write list')
			self.on_event(
				device=_system_device('write_list'),
				event_type='remove_from_write_list',
				event_data={**tag, 'original_epc': self.write_list[tid]['original_epc']},
			)
			del self.write_list[tid]
			if not self.write_list:
				logging.info('Write list is now empty')
				self.on_event(
					device=_system_device('write_list'),
					event_type='write_list_empty',
					event_data={},
				)
				return True
		return False

	def clear_write_list(self):
		self.write_list.clear()
		logging.info('Cleared write list')
		self.on_event(
			device=_system_device('write_list'),
			event_type='write_list_cleared',
			event_data={},
		)

	async def check_target(self, tag: dict):
		target = tag.get('target')
		if not target:
			return
		if tag.get('epc') == tag.get('target'):
			logging.info(f"Tag {tag.get('tid')} already has target EPC, removing from write list")
			tag['target'] = None
			self.remove_from_write_list(tag)
			return
		await self.devices.write_epc(
			device_name=tag.get('device'),
			write_tag=WriteTagValidator(
				target_identifier='tid',
				target_value=tag.get('tid'),
				new_epc=tag.get('target'),
				password='00000000',
			),
		)

	# Operation management
	def set_operation(self, operation: str):
		operation = operation.strip().lower()
		valid_operations = ['ptl', 'single']
		if operation not in valid_operations:
			raise ValueError(f'Operação inválida: {operation}')
		self.operation = operation
		self.tags.clear()
		self._single_saved_tags.clear()
		self.clear_support()

	def cancel_operation(self):
		self.operation = None

	# ------------------------------------------------------------------ #
	# AS400 Setup                                                          #
	# ------------------------------------------------------------------ #

	def setup_as_400(self):
		logging.info('Setting up AS400 database connection...')
		try:
			if settings.AS400_URL is None or self.db_user is None or self.db_password is None:
				logging.warning(
					'AS400_URL or database credentials are not set. Skipping AS400 database setup.'
				)
				logging.warning(
					f'Current settings - AS400_URL: {settings.AS400_URL}, DB_USER: {self.db_user}, DB_PASSWORD: {self.db_password}'
				)
				return False, 'Credenciais ou URL do AS400 não configurados.'

			logging.info(f'Initializing AS400 DatabaseManager with URL: {settings.AS400_URL}')
			db_url = settings.AS400_URL.format(DB_USER=self.db_user, DB_PASSWORD=self.db_password)
			local_db_url = not settings.AS400_URL.startswith('db2')
			if not local_db_url:
				self.as_400 = DatabaseManager(
					database_url=db_url,
					pool_size=5,
					pool_timeout=5,
					connect_args={'timeout': 5},
					execution_options={'timeout': 5},
					isolation_level='AUTOCOMMIT',
				)
			else:
				self.as_400 = DatabaseManager(
					database_url=db_url,
				)
			self.as_400.initialize()

			# Quick verification query to catch driver/connection issues early
			if not local_db_url:
				try:
					self.as_400.execute_query('select 1 from sysibm.sysdummy1')
					logging.info('AS400 test query succeeded')
				except Exception:
					logging.exception(
						'AS400 test query failed; verify AS400_URL, ODBC driver and DB status'
					)
					return False, 'Falha ao conectar, verifique URL e Credenciais do AS400.'
			else:
				try:
					self.as_400.execute_query('select 1')
					logging.info('AS400 test query succeeded')
				except Exception:
					logging.exception(
						'AS400 test query failed; verify AS400_URL, ODBC driver and DB status'
					)
					return False, 'Falha ao conectar, verifique URL e Credenciais do AS400.'

			logging.info('AS400 database connection established.')

			return True, 'AS400 database connection established.'

		except Exception as e:
			logging.error(f'Error setting up AS400 database: {e}')
			return False, str(e)

	def ensure_as_400(self):
		if self.as_400 is None:
			success, data = self.setup_as_400()
			if not success:
				logging.error(f'AS400 database is not set up: {data}')
				return False
		return True

	# querys
	def get_data_by_support(self, support: str):
		if not self.ensure_as_400():
			raise ValueError('AS400 database is not available.')
		query = """
			SELECT pedido, suporte, sku, descricao, ean, quantidade, posicao
			FROM supconf
			WHERE UPPER(TRIM(SUPORTE)) = :support OR UPPER(TRIM(posicao)) = :support
		"""
		result = self.as_400.execute_query(query, {'support': support})
		logging.info(f'Query result for support {support}: {result}')
		return result

	def get_single_data(self, support: str):
		if not self.ensure_as_400():
			raise ValueError('AS400 database is not available.')
		query = """
			SELECT pedido, suporte, sku, descricao, ean, quantidade, posicao
			FROM supconfsig
			WHERE UPPER(TRIM(AGRUPADO)) = :support
		"""
		params = {'support': support}
		result = self.as_400.execute_query(query, params)
		logging.info(f'Single lookup result for support {support}: {result}')
		return result

	def _save_single_tag(self, tag: dict):
		if not self.ensure_as_400():
			raise ValueError('AS400 database is not available.')

		identifier = tag.get('tid') or tag.get('epc')
		if not identifier or identifier in self._single_saved_tags:
			return False

		gtin = tag.get('gtin')
		if not gtin:
			try:
				gtin = SGTIN.decode(tag.get('epc')).gtin
			except Exception:
				return False
		gtin = str(gtin).strip().upper()

		matching_rows = []
		for row in self.support_data.data:
			eans = {
				ean.strip().upper() for ean in str(row.get('ean') or '').split(';') if ean.strip()
			}
			if gtin in eans:
				matching_rows.append(row)
		if not matching_rows:
			logging.warning(
				'Single tag GTIN %s is not in group %s', gtin, self.support_data.support
			)
			return False

		# Do not record more units of this GTIN than the group contains.
		gtin_aliases = {
			ean.strip().upper()
			for row in matching_rows
			for ean in str(row.get('ean') or '').split(';')
			if ean.strip()
		}
		current_counts = self.tags.get_gtin_counts()
		found = sum(
			count
			for current_gtin, count in current_counts.items()
			if str(current_gtin).strip().upper() in gtin_aliases
		)
		expected = sum(row.get('quantidade', 0) or 0 for row in matching_rows)
		if found > expected:
			logging.warning('Ignoring excess Single tag for GTIN %s', gtin)
			return False

		row = matching_rows[0]
		support = row.get('suporte') or self.support_data.support
		try:
			support_number = Decimal(str(support).strip())
			if (
				not support_number.is_finite()
				or support_number < 0
				or support_number != support_number.to_integral_value()
			):
				raise InvalidOperation
			support = format(support_number.to_integral_value(), 'f')
		except (InvalidOperation, TypeError, ValueError) as error:
			raise ValueError(f'Suporte inválido para gravar em logconf: {support}') from error

		query = """
			INSERT INTO logconf
				(suporte, bancada, data, hora, usuario, embalagem, status, codpro, quantidade, sinal)
			VALUES
				(:suporte, :bancada, CURRENT_DATE, CURRENT_TIME, :usuario, :embalagem,
				 :status, :codpro, :quantidade, :sinal)
		"""
		params = {
			'suporte': support,
			'bancada': 1,
			'usuario': self.db_user,
			'embalagem': settings.EMBALAGEM,
			'status': 'OK',
			'codpro': row.get('sku'),
			'quantidade': 1,
			'sinal': '=',
		}
		with self.as_400.get_session() as session:
			self.as_400.execute_query(query, params, session=session)
		self._single_saved_tags.add(identifier)
		logging.info('Saved Single tag %s (GTIN %s) to logconf', identifier, gtin)
		return True

	def get_today_count(self):
		if not self.ensure_as_400():
			raise ValueError('AS400 database is not available.')
		query = """
			SELECT COUNT(DISTINCT suporte) AS total
			FROM (
				SELECT suporte
				FROM logconf
				WHERE data = CURRENT_DATE AND embalagem = :embalagem
				UNION
				SELECT suporte
				FROM logconfdiv
				WHERE data = CURRENT_DATE AND embalagem = :embalagem
			) AS today_supports
		"""
		result = self.as_400.execute_query(query, {'embalagem': settings.EMBALAGEM})
		return result

	def _save_finish_comparison(self, comparison: list[dict], successful: bool):
		if not self.ensure_as_400():
			raise ValueError('AS400 database is not available.')

		table = 'logconf' if successful else 'logconfdiv'
		status_codes = {'=': 'OK', '<': 'FAL', '>': 'SOB', '!': 'DIV'}
		if successful:
			query = """
				INSERT INTO logconf
					(suporte, bancada, data, hora, usuario, embalagem, status, codpro, quantidade, sinal)
				VALUES
					(:suporte, :bancada, CURRENT_DATE, CURRENT_TIME, :usuario, :embalagem,
					 :status, :codpro, :quantidade, :sinal)
			"""
		else:
			query = """
				INSERT INTO logconfdiv
					(suporte, bancada, data, hora, usuario, embalagem, status, codpro,
					 quantidade, sinal, qtesperada)
				VALUES
					(:suporte, :bancada, CURRENT_DATE, CURRENT_TIME, :usuario, :embalagem,
					 :status, :codpro, :quantidade, :sinal, :qtesperada)
			"""

		with self.as_400.get_session() as session:
			params_list = []
			for item in comparison:
				support = item.get('suporte') or self.support_data.support
				try:
					support_number = Decimal(str(support).strip())
					if (
						not support_number.is_finite()
						or support_number < 0
						or support_number != support_number.to_integral_value()
					):
						raise InvalidOperation
					support = format(support_number.to_integral_value(), 'f')
				except (InvalidOperation, TypeError, ValueError) as error:
					raise ValueError(
						f'Suporte inválido para gravar em {table}: {support}'
					) from error

				params = {
					'suporte': support,
					'bancada': 1,
					'usuario': self.db_user,
					'embalagem': settings.EMBALAGEM,
					'status': status_codes.get(item.get('status'), 'DIV'),
					'codpro': item.get('sku'),
					'quantidade': item.get('encontrado', 0),
					'sinal': item.get('status', '='),
				}
				if not successful:
					params['qtesperada'] = item.get('esperado', 0)
				params_list.append(params)

			if params_list:
				self.as_400.execute_query(query, params_list, session=session)

	# Support management
	def set_support(self, support: str):
		try:
			support = support.strip().upper().lstrip('0')
			if not support:
				raise ValueError('Suporte não pode ser vazio')
			data = self.get_data_by_support(support)
			if support == 'TESTE':
				data = [
					{
						'PEDIDO': '0000001',
						'SUPORTE': 'TESTE',
						'SKU': '0107727063UNI7',
						'DESCRICAO': 'PRODUTO DE TESTE',
						'EAN': '07321738302796',
						'QUANTIDADE': 3,
					},
					{
						'PEDIDO': '0000002',
						'SUPORTE': 'TESTE',
						'SKU': '0107727063UNI8',
						'DESCRICAO': 'PRODUTO DE TESTE 2',
						'EAN': '7891234567895',
						'QUANTIDADE': 5,
					},
				]

			if not data:
				raise ValueError('Suporte inválido ou não encontrado')

			# lower all string values in the data
			data = [{key.lower(): value for key, value in row.items()} for row in data]
			if any(not row.get('quantidade') for row in data):
				raise ValueError('Pedido incompleto ou com erro')

			self.support_data = SupportData(support=support, data=data)
			self.tags.clear()
		except ValueError as e:
			logging.error(f'Error setting support: {e}')
			raise e

	def set_single_support(self, support: str):
		if getattr(self, 'operation', None) != 'single':
			raise ValueError('A operação atual não é Single')
		support = support.upper().strip().lstrip('0')
		if not support:
			raise ValueError('Defina o agrupado')

		data = self.get_single_data(support)
		if not data:
			raise ValueError('Nenhum produto encontrado para esse agrupado')

		data = [{key.lower(): value for key, value in row.items()} for row in data]
		if any(not row.get('quantidade') for row in data):
			raise ValueError('Pedido incompleto ou com erro')

		self.support_data = SupportData(support=support, data=data)
		self.tags.clear()
		self._single_saved_tags.clear()

	def clear_support(self):
		self.support_data = None
		self.tags.clear()
		self._single_saved_tags.clear()

	def compare_tags(self):
		if not self.support_data:
			return []
		data = []
		current_tags = self.tags.get_gtin_counts()
		current_data = self.support_data.data.copy()
		for row in current_data:
			eans = {ean.strip() for ean in str(row.get('ean') or '').split(';') if ean.strip()}
			row['encontrado'] = sum(current_tags.pop(ean, 0) for ean in eans)
			current = row.get('quantidade')
			found = row.get('encontrado')
			if found < current:
				row['status'] = '<'
			elif found > current:
				row['status'] = '>'
			else:
				row['status'] = '='
			data.append(
				{
					'pedido': row.get('pedido', ''),
					'suporte': row.get('suporte', ''),
					'sku': row.get('sku', ''),
					'descricao': row.get('descricao', ''),
					# "ean": row.get('ean', ''),
					'esperado': row.get('quantidade', 0),
					'encontrado': row.get('encontrado', 0),
					'status': row.get('status', ''),
				}
			)

		data += [
			{
				'pedido': '',
				'suporte': '',
				'sku': gtin,
				'descricao': 'Divergente',
				# "ean": gtin,
				'esperado': 0,
				'encontrado': count,
				'status': '!',
			}
			for gtin, count in current_tags.items()
		]
		status_order = {'!': 0, '>': 1, '<': 2, '=': 3}
		return sorted(data, key=lambda row: status_order.get(row.get('status'), len(status_order)))

	def can_finish(self):
		if not self.support_data:
			return {'can_finish': False, 'reason': 'Sem suporte definido'}
		data = self.compare_tags()
		if data and self.tags.get_all(1):
			return {'can_finish': True, 'reason': ''}
		return {'can_finish': False, 'reason': 'Sem Tags encontradas'}

	def finish(self):
		if not self.support_data:
			raise ValueError('Sem suporte definido')
		if not self.can_finish().get('can_finish'):
			raise ValueError('Existem divergências nos dados')

		comparison = self.compare_tags()
		if self.operation != 'single':
			successful = all(item.get('status') == '=' for item in comparison)
			self._save_finish_comparison(comparison, successful)

		# Mark the operation as finished
		self.support_data = None

	def get_epc_by_gtin(self, gtin):
		self.last_serial_gtin += 1
		try:
			epc = SGTIN.from_sgtin(gtin, self.last_serial_gtin, 7).encode().lower()
		except Exception as e:
			logging.error(f'Failed to generate EPC for GTIN {gtin}: {e}')
			epc = None

		# try to decode the EPC back to GTIN
		try:
			decoded_gtin = SGTIN.decode(epc).gtin
		except Exception as e:
			logging.error(f'Failed to decode EPC {epc}: {e}')
			decoded_gtin = None
		if not epc:
			raise ValueError('Falha ao gerar EPC')
		if not decoded_gtin == gtin:
			raise ValueError('Falha ao decodificar EPC')
		return epc
