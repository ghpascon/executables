from smartx_rfid.license import LicenseManager
from app.core import LICENSE_PATH
import logging

PUBLIC_KEY_PATH = LICENSE_PATH / 'public_key.pem'
LICENSE_STR_PATH = LICENSE_PATH / 'license.txt'

# Load public key
try:
	with open(PUBLIC_KEY_PATH, 'r') as f:
		PUBLIC_KEY = f.read()
except Exception as e:
	logging.error(f'Error loading public key: {e}')
	PUBLIC_KEY = None

# Load license string
try:
	with open(LICENSE_STR_PATH, 'r') as f:
		LICENCE_STR = f.read()
except Exception as e:
	logging.error(f'Error loading license string: {e}')
	LICENCE_STR = None

# Initialize License Manager
license_manager = LicenseManager(
	public_key_pem=PUBLIC_KEY,
)
try:
	license_manager.load_license(LICENCE_STR)
	logging.info(f'License data: {license_manager.license_data}')
except Exception as e:
	logging.error(f'Error loading license: {e}')
