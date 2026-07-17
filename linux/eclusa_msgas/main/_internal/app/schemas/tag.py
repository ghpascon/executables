import re
from typing import Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class TagSchema(BaseModel):
    device: str = Field("DEVICE01")
    epc: str = Field("000000000000000000000001")
    tid: Optional[str] = Field("000000000000000000000001")
    ant: Optional[int] = 0
    rssi: Optional[int] = 0

    @field_validator("epc", "tid")
    def validate_epc_length_and_hex(cls, v, field):
        if v is None:
            return v
        if len(v) != 24:
            raise ValueError(f"{field.name} must have exactly 24 characters")
        if not re.fullmatch(r"[0-9a-fA-F]{24}", v):
            raise ValueError(f"{field.name} must contain only hexadecimal characters (0-9, a-f)")
        return v.lower()


class WriteTagValidator(BaseModel):
    target_identifier: Optional[str] = Field(
        None, description='Identifier type: "epc", "tid", or None'
    )
    target_value: Optional[str] = Field(
        None, description="Current value of the identifier (24 hexadecimal characters)"
    )
    new_epc: str = Field(..., description="New EPC value to write (24 hexadecimal characters)")
    password: str = Field(..., description="Password to access the tag (8 hexadecimal characters)")

    @field_validator("target_identifier")
    def validate_identifier(cls, v):
        if v == "None" or v is None:
            return None
        allowed_values = ("epc", "tid", None)
        if v not in allowed_values:
            raise ValueError(f"target_identifier must be one of {allowed_values}")
        return v.lower()

    @field_validator("target_value", "new_epc")
    def validate_epc_length_and_hex(cls, v, field):
        if v is None or v == "None":
            v = "0" * 24

        if len(v) != 24:
            raise ValueError(f"{field.name} must have exactly 24 characters")
        if not re.fullmatch(r"[0-9a-fA-F]{24}", v):
            raise ValueError(f"{field.name} must contain only hexadecimal characters (0-9, a-f)")
        return v.upper()

    @field_validator("password")
    def validate_password_length_and_hex(cls, v, field):
        if len(v) != 8:
            raise ValueError(f"{field.name} must have exactly 8 characters")
        if not re.fullmatch(r"[0-9a-fA-F]{8}", v):
            raise ValueError(f"{field.name} must contain only hexadecimal characters (0-9, a-f)")
        return v.upper()  # Opcional: retorna sempre em maiúsculas



class TagRequest(BaseModel):
    device: str = Field(default="DEVICE_01")
    epc: str = Field(default="000000000000000000000001")
    tid: Optional[str] = Field(default="000000000000000000000002")
    ant: Optional[int] = Field(default=1)
    rssi: Optional[int] = Field(default=-80)

    @field_validator("epc", "tid")
    def validate_epc_length_and_hex(cls, v, info):
        if v is None:
            return v
        if len(v) != 24:
            raise ValueError(f"{info.field_name} must have exactly 24 characters")
        if not re.fullmatch(r"[0-9a-fA-F]{24}", v):
            raise ValueError(
                f"{info.field_name} must contain only hexadecimal characters (0-9, a-f)"
            )
        return v.lower()

    @field_validator("rssi")
    def validate_rssi(cls, v):
        if v is None:
            return -80
        if not isinstance(v, int):
            raise ValueError("rssi must be an integer")
        return -abs(v)  # força negativo

    @field_validator("ant")
    def validate_ant(cls, v):
        return v if v is not None else 1


class TagRequestSimulator(BaseModel):
    device: Optional[str] = Field("DEVICE_01")
    epc: str = Field("000000000000000000000001")
    tid: Optional[str] = Field("000000000000000000000002")
    ant: int = Field(1)
    rssi: int = Field(-80)

    @field_validator("epc", "tid")
    def validate_epc_length_and_hex(cls, v, info: ValidationInfo):
        if v is None:
            return v
        if len(v) != 24:
            raise ValueError(f"{info.field_name} must have exactly 24 characters")
        if not re.fullmatch(r"[0-9a-fA-F]{24}", v):
            raise ValueError(
                f"{info.field_name} must contain only hexadecimal characters (0-9, a-f)"
            )
        return v

class TagListSimulator(BaseModel):
    device: str = Field("DEVICE01")
    start_epc: str = Field("000000000000000000000001")
    qtd: int = 50

    @field_validator("start_epc")
    def validate_epc_length_and_hex(cls, v, info: ValidationInfo):
        if len(v) != 24:
            raise ValueError(f"{info.field_name} must have exactly 24 characters")
        if not re.fullmatch(r"[0-9a-fA-F]{24}", v):
            raise ValueError(
                f"{info.field_name} must contain only hexadecimal characters (0-9, a-f)"
            )
        return v.lower()
