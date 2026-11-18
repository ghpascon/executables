import re

from pydantic import BaseModel, Field, ValidationInfo, field_validator
from smartx_rfid.utils.regex import regex_hex


class ProtectedInventoryModel(BaseModel):
	active: bool = Field(True)
	password: str = Field('12345678')

	@field_validator('password')
	def validate_password_length(cls, v, info: ValidationInfo):
		if len(v) != 8:
			raise ValueError(f'{info.field_name} must have exactly 8 characters')
		if not re.fullmatch(r'[0-9a-fA-F]{8}', v):
			raise ValueError(
				f'{info.field_name} must contain only hexadecimal characters (0-9, a-f)'
			)
		return v.lower()


class ProtectedModeModel(ProtectedInventoryModel):
	epc: str = Field('000000000000000000000001')

	@field_validator('epc')
	def validate_epc_length_and_hex(cls, v, info: ValidationInfo):
		if not regex_hex(v):
			raise ValueError(
				f'{info.field_name} must contain only hexadecimal characters (0-9, a-f) and have exactly 24 characters'
			)
		return v.lower()


class ProtectListModel(ProtectedInventoryModel):
	epcs: list[str] = Field(['000000000000000000000001', '000000000000000000000002'])

	@field_validator('epcs')
	def validate_epc_length_and_hex(cls, v, info: ValidationInfo):
		for epc in v:
			if not regex_hex(epc):
				raise ValueError(
					f'{info.field_name} must contain only hexadecimal characters (0-9, a-f) and have exactly 24 characters'
				)
		return [epc.lower() for epc in v]
