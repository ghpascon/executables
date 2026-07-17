import json
import logging
from typing import Any, Optional

from pydantic import BaseModel, Field


def load_example_from_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.info(f"Erro ao carregar JSON de exemplo: {e}")
        return {}



class ActionsRequest(BaseModel):
    HTTP_POST: Optional[str] = Field("http://localhost:5001")
    DATABASE_URL: Optional[str] = Field(
        "mysql+aiomysql://root:admin@localhost:3306/middleware_smartx"
    )
    MQTT_URL: Optional[str] = Field(
        "mqtt://localhost:1883/connector"
    ) 

    XTRACK_URL: Optional[str] = Field("https://192.168.0.100:6100/req")
    STORAGE_DAYS: int = Field(0)
    LOG_PATH: str = Field("Logs")

class EventRequest(BaseModel):
    device: str = Field("DEVICE01")
    event_type: str = Field("event_type")
    event_data: Any = {"data": "xyz"}