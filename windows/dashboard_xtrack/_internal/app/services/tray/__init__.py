from ._main import TrayManager
from app.core import settings
from app.core import ICON_PATH

tray_manager = TrayManager(app_name=settings.TITLE, icon_path=ICON_PATH)
