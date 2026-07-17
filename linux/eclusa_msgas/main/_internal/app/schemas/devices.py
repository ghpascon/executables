from typing import Optional, Tuple

from pydantic import BaseModel, Field

from app.services.devices import devices


def validate_device(device: str, need_connected: bool = True) -> Tuple[bool, str | dict]:
    """
    Validate if the device exists and optionally if it is connected.
    """
    if device not in devices.get_device_list():
        return False, "Invalid Device"

    if not devices.devices.get(device).is_connected and need_connected:
        return False, "Device is not connected"

    return True, {"msg": "success"}



class BooleanDeviceRequest(BaseModel):
    device: str = Field("DEVICE01")
    state: bool = True



class SetGpoRequest(BaseModel):
    device: str = Field("DEVICE01")
    pin: Optional[int] = Field(1)
    state: Optional[bool] = Field(True)
    control: Optional[str] = Field("static")
    time: Optional[int] = Field(1000)


