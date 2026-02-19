from pydantic import Field, field_validator, BaseModel
from smartx_rfid.schemas.tag import regex_hex


class OrderSchema(BaseModel):
	order: str = Field('ORDER_01')
	epc: str = Field('000000000000000000000001')
	description: str = Field('epc description')

	@field_validator('epc')
	def validate_epc(cls, value):
		if not regex_hex(value, length=24):
			raise ValueError('Invalid EPC format')
		return value.lower()
