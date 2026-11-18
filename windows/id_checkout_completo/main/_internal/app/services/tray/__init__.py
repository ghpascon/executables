import logging

from .command import restart_application as _restart_application
from .command import exit_application as _exit_application

try:
	from ._main import TrayManager
	from app.core import settings
	from app.core import ICON_PATH

	tray_manager = TrayManager(app_name=settings.TITLE, icon_path=ICON_PATH)
except Exception as e:
	logging.warning(f'TrayManager não pôde ser iniciado: {e}\nO sistema continuará sem tray.')

	class DummyTrayManager:
		def restart_application(self, *args, **kwargs):
			logging.info('Reiniciando aplicação (dummy, sem tray)')
			_restart_application()

		def exit_application(self, *args, **kwargs):
			logging.info('Encerrando aplicação (dummy, sem tray)')
			_exit_application()

	tray_manager = DummyTrayManager()
