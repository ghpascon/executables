from ._main import XtackManager
from app.core import settings

xtrack_manager = XtackManager(settings.XTRACK_URL)
