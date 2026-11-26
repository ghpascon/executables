from pydantic import BaseModel, Field, field_validator
from smartx_rfid.utils.regex import regex_hex


class WriteListPrefixModel(BaseModel):
	epcs: list[str] = Field(
		['000000000000000000000001', '000000000000000000000002'],
		description='List of tags to be written',
	)
	prefix: str = Field('abc', description='Prefix to be added to the tags in the write list')

	@field_validator('prefix')
	def validate_prefix(cls, value: str) -> str:
		if not regex_hex(value):
			raise ValueError(f'Prefix {value!r} is not a valid hexadecimal string')
		return value.lower()

	@field_validator('epcs')
	def validate_epcs(cls, value: list[str]) -> list[str]:
		if not isinstance(value, (list, tuple)):
			raise TypeError('epcs must be a list of hexadecimal strings')
		invalid = [epc for epc in value if not regex_hex(epc)]
		if invalid:
			raise ValueError(f'Invalid EPC(s): {invalid}')
		return [v.lower() for v in value]
