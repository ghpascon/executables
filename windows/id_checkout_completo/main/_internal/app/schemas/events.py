from pydantic import Field
from smartx_rfid.schemas.events import EventSchema


class EventDeviceSchema(EventSchema):
	device_name: str = Field(..., description='Name of the device associated with the event')
	device_serial_number: str | None = Field(
		None,
		description=(
			'Serial number of the device associated with the event. '
			'When omitted, it is resolved from the connected device with the same name (if any).'
		),
	)
