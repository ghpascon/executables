import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.path import get_prefix_from_path
from app.schemas.devices import SetGpoRequest, validate_device
from app.schemas.responses import config_responses, device_list_responses, gpo_responses
from app.services.devices import devices

router_prefix = get_prefix_from_path(__file__)
router = APIRouter(prefix=router_prefix, tags=[router_prefix])


@router.get(
    "/get_device_list",
    responses=device_list_responses,
    summary="Get all device names",
    description="Returns a list of all registered device names.",
)
async def api_get_device_list():
    return devices.get_device_list()


@router.get(
    "/get_device_config/{device_name}",
    responses=config_responses,
    summary="Get device configuration",
    description="Returns the current configuration of the specified device.",
)
async def get_device_config(device_name: str):
    try:
        status, msg = validate_device(device=device_name, need_connected=False)
        if not status:
            raise HTTPException(status_code=422, detail=msg)
        return devices.devices.get(device_name).config
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/get_device_types_list",
    responses=device_list_responses,
    summary="Get list of supported device types",
    description="Returns a list of supported device types that can be configured.",
)
async def api_get_device_types_list():
    return await devices.get_device_types()


@router.get(
    "/get_example_config/{device_name}",
    responses=config_responses,
    summary="Get example config for a device type",
    description="Returns an example configuration for a given device type.",
)
async def get_example_config(device_name: str):
    try:
        return await devices.get_example_config(device_name)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/create_device/{device_name}",
    summary="Create a new device",
    description="Creates a new device with the given name and configuration.",
)
async def create_device(device_name: str, data: dict):
    try:
        return await devices.create_device(data, device_name)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/update_device/{device_name}",
    summary="Update an existing device",
    description="Updates the configuration of an existing device.",
)
async def update_device(device_name: str, data: dict):
    try:
        status, msg = validate_device(device=device_name, need_connected=False)
        if not status:
            raise HTTPException(status_code=422, detail=msg)
        return await devices.update_device(data, device_name)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/delete_device/{device_name}",
    summary="Delete a device",
    description="Deletes the specified device from the system.",
)
async def delete_device(device_name: str):
    try:
        status, msg = validate_device(device=device_name, need_connected=False)
        if not status:
            raise HTTPException(status_code=422, detail=msg)
        return await devices.delete_device(name=device_name)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/write_gpo",
    responses=gpo_responses,
    summary="Write GPO state",
    description="Sends a GPO command to the device using JSON payload.",
    name="writegpo",
)
async def write_gpo(data: SetGpoRequest):
    try:
        payload = data.model_dump()
        device = payload.get("device", "")
        # 1. Validação do dispositivo
        try:
            status, msg = validate_device(device=device, need_connected=False)
            if not status:
                raise HTTPException(status_code=422, detail=msg)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"{str(e)}")

        # 2. Monta os dados a partir do JSON e executa o comando
        try:
            gpo_data = {
                "pin": payload.get("gpo_pin", 1),
                "state": payload.get("state", True),
                "control": payload.get("control", "static"),
                "time": payload.get("time", 1000),
            }

            result = await devices.write_gpo(device, **gpo_data)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"{str(e)}")

        # 3. Resposta final
        if result:
            logging.info(f"write_gpo -> {device} - {gpo_data['state']}")
            return {"msg": f"GPO {device}, {gpo_data['state']}"}
        else:
            logging.warning(f"{device} não possui GPO configurado")
            return JSONResponse(
                status_code=404, content={"msg": f"Dispositivo {device} não possui GPO"}
            )

    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        return JSONResponse(status_code=500, content={"msg": f"Erro interno inesperado: {str(e)}"})


@router.get(
    "/get_device_state/{device}",
    summary="Get device state",
    description=(
        "Returns the current state of the device as both a numeric code and a description.\n"
        "-1: Device not found | 0: Disconnected | 1: Connected | 2: Reading"
    ),
)
async def get_device_state(request: Request, device: str):
    """Return device state with numeric code and human-readable description."""
    if device not in devices.devices:
        state = -1
        description = "Device not found"
        return {"state": state, "description": description}

    reader = devices.devices[device]

    if not reader.is_connected:
        state = 0
        description = "Disconnected"
    elif hasattr(reader, "is_reading") and reader.is_reading:
        state = 2
        description = "Reading"
    else:
        state = 1
        description = "Connected"

    return {"state": state, "description": description}
