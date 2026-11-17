import json
import logging
import os


class Settings:
	def __init__(self, config_path):
		"""Application settings loader and manager."""
		self._config_path = config_path
		self.load()

	def load(self, data: dict | None = None):
		"""Load configuration from JSON file."""
		if data is None:
			data = {}

			if os.path.exists(self._config_path):
				try:
					with open(self._config_path, 'r', encoding='utf8') as f:
						data = json.load(f)
				except Exception as e:
					logging.error(f'Error loading {self._config_path}: {e}')

		# Replace all empty string values with None recursively
		def replace_empty_with_none(obj):
			if isinstance(obj, dict):
				return {k: replace_empty_with_none(v) for k, v in obj.items()}
			elif isinstance(obj, list):
				return [replace_empty_with_none(v) for v in obj]
			elif obj == '':
				return None
			else:
				return obj

		data = replace_empty_with_none(data)

		# Load variables with defaults
		self.TITLE: str = data.get('TITLE', 'CHECKOUT')
		if not isinstance(self.TITLE, str) or len(self.TITLE) == 0:
			self.TITLE = ' '

		self.LOG_PATH: str = data.get('LOG_PATH', 'Logs')

		self.STORAGE_DAYS: int = data.get('STORAGE_DAYS', 7)

		self.OPEN_BROWSER: bool = data.get('OPEN_BROWSER', True)
		self.BEEP: bool = data.get('BEEP', False)

		self.CLEAR_OLD_TAGS_INTERVAL: int | None = data.get('CLEAR_OLD_TAGS_INTERVAL', None)
		if (
			not isinstance(self.CLEAR_OLD_TAGS_INTERVAL, int)
			or self.CLEAR_OLD_TAGS_INTERVAL < 0
			or self.CLEAR_OLD_TAGS_INTERVAL > 3600
		):
			self.CLEAR_OLD_TAGS_INTERVAL = 3600  # Default to 1 hour

		self.TAG_PREFIX: str | None | list[str] = data.get('TAG_PREFIX', None)
		if not isinstance(self.TAG_PREFIX, (str, list)):
			self.TAG_PREFIX = None

		self.ALWAYS_SEND: bool = data.get('ALWAYS_SEND', False)
		if not isinstance(self.ALWAYS_SEND, bool):
			self.ALWAYS_SEND = False

		self.WEBHOOK_URL: str | None = data.get('WEBHOOK_URL', None)
		self.DATABASE_URL: str | None = data.get('DATABASE_URL', None)
		self.XTRACK_URL: str | None = data.get('XTRACK_URL', None)

		self.PORT: int = data.get('PORT', 5000)
		self.CLEAR_ON_START: bool = data.get('CLEAR_ON_START', True)
		self.ONLY_COMPLETE_TABLE: bool = data.get('ONLY_COMPLETE_TABLE', True)

		self.ALLOW_EXTERNAL_CONNECTIONS: bool = data.get('ALLOW_EXTERNAL_CONNECTIONS', False)
		if not isinstance(self.ALLOW_EXTERNAL_CONNECTIONS, bool):
			self.ALLOW_EXTERNAL_CONNECTIONS = False
		self.AS400_URL: str | None = data.get('AS400_URL', None)


		self.DB_USER: str | None = data.get('DB_USER', None)
		self.DB_PASSWORD: str | None = data.get('DB_PASSWORD', None)

		if not isinstance(self.AS400_URL, str) or \
			len(self.AS400_URL) == 0 or \
			not "{DB_USER}" in self.AS400_URL or \
			not "{DB_PASSWORD}" in self.AS400_URL:
			logging.error('AS400_URL is not properly configured.')

		if not isinstance(self.DB_USER, str) or len(self.DB_USER) == 0:
			logging.error('DB_USER is not properly configured.')
		if not isinstance(self.DB_PASSWORD, str) or len(self.DB_PASSWORD) == 0:
			logging.error('DB_PASSWORD is not properly configured.')

		self.EMBALAGEM: str | None = data.get('EMBALAGEM', "HEM")

		self.AS400_URL_: str | None = data.get('AS400_URL_', None)
		self.save()  # Save default config if file doesn't exist


	def get_current_settings(self):
		return {
			key: value
			for key, value in vars(self).items()
			if not key.startswith('_') and not callable(value)
		}

	def save(self):
		"""Save all instance attributes except _config_path to JSON file."""
		try:
			logging.info(f'Saving config to: {self._config_path}')

			# Dynamically get all attributes except _config_path
			data = self.get_current_settings()

			# Make sure folder exists
			os.makedirs(os.path.dirname(self._config_path), exist_ok=True)

			with open(self._config_path, 'w', encoding='utf8') as f:
				json.dump(data, f, indent=4, ensure_ascii=False)

		except Exception as e:
			logging.error(f'Error saving config: {e}')
