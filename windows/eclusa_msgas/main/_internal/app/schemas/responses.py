# === Swagger Response Examples ===
from app.schemas.events import load_example_from_json

device_list_responses = {
    200: {
        "description": "List of all registered device names.",
        "content": {"application/json": {"example": ["device_01", "device_02"]}},
    }
}

device_responses = {
    200: {
        "description": "Successful operation.",
        "content": {"application/json": {"example": {"msg": "success"}}},
    },
    422: {
        "description": "Device validation error.",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_device": {
                        "summary": "Invalid device name",
                        "value": {"detail": "Invalid Device"},
                    },
                    "device_not_connected": {
                        "summary": "Device is disconnected",
                        "value": {"detail": "Device is not connected"},
                    },
                }
            }
        },
    },
    500: {
        "description": "Unexpected internal error.",
        "content": {"application/json": {"example": {"detail": "Internal Server Error"}}},
    },
}

config_responses = {
    200: {
        "description": "Returns the configuration of the specified device.",
        "content": {
            "application/json": {
                "example": {
                    "READER": "X714",
                    "CONNECTION": "COM5",
                    "PARAMETER": "VALUE",
                }
            }
        },
    },
    422: {
        "description": "Invalid device or configuration error.",
        "content": {"application/json": {"example": {"detail": "Invalid Device"}}},
    },
    500: {
        "description": "Internal server error.",
        "content": {"application/json": {"example": {"detail": "Internal Server Error"}}},
    },
}

state_responses = {
    200: {
        "description": "Returns the current reading state of the device.",
        "content": {
            "application/json": {
                "examples": {
                    "idle": {"summary": "Device is idle", "value": {"state": "idle"}},
                    "running": {
                        "summary": "Device is actively reading",
                        "value": {"state": "running"},
                    },
                }
            }
        },
    },
    422: {
        "description": "Device validation error.",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_device": {
                        "summary": "Invalid device name",
                        "value": {"detail": "Invalid Device"},
                    },
                    "device_not_connected": {
                        "summary": "Device is disconnected",
                        "value": {"detail": "Device is not connected"},
                    },
                }
            }
        },
    },
    500: {
        "description": "Internal server error.",
        "content": {"application/json": {"example": {"detail": "Internal Server Error"}}},
    },
}


gpo_responses = {
    200: {
        "description": "GPO command executed successfully",
        "content": {"application/json": {"example": {"msg": "GPO DEVICE_01, True"}}},
    },
    400: {
        "description": "Invalid device",
        "content": {"application/json": {"example": {"detail": "Invalid device"}}},
    },
    404: {
        "description": "No GPO found for device",
        "content": {"application/json": {"example": {"msg": "No Gpo"}}},
    },
    422: {
        "description": "Validation error",
        "content": {"application/json": {"example": {"detail": "Invalid device"}}},
    },
    500: {
        "description": "Internal Server Error",
        "content": {"application/json": {"example": {"msg": "Exception message"}}},
    },
}

rfid_base_responses = {
    200: {
        "description": "Operation successful",
        "content": {"application/json": {"example": {"msg": "success"}}},
    },
    422: {
        "description": "Validation error",
        "content": {"application/json": {"example": {"detail": "error"}}},
    },
}

rfid_actions_responses = {
    200: {
        "description": "RFID action settings returned successfully",
        "content": {
            "application/json": {"example": load_example_from_json("config/examples/actions.json")}
        },
    },
    422: {
        "description": "Invalid input or action",
        "content": {"application/json": {"example": {"detail": "error"}}},
    },
}
