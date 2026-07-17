import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.core.path import get_prefix_from_path
from app.schemas.devices import BooleanDeviceRequest
from app.schemas.events import EventRequest
from app.schemas.tag import TagListSimulator, TagRequestSimulator
from app.schemas.responses import rfid_base_responses
from app.services.events import events

router_prefix = get_prefix_from_path(__file__)
router = APIRouter(prefix=router_prefix, tags=[router_prefix])


@router.post(
    "/tag",
    responses=rfid_base_responses,
    summary="Simulate RFID tag read",
    description="Simulates an RFID tag being read and sends the data to the tag processing logic.",
)
async def simulator_tag(tag: TagRequestSimulator):
    try:
        await events.on_tag(tag.model_dump())
        return {"msg": "success"}
    except Exception as e:
        logging.error(f"Error while processing tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/tag_list",
    summary="Simulate RFID sequential tag list",
    description="Simulates an RFID tag list being read and sends the data to the tag processing logic.",
)
async def tag_list(tag_generator: TagListSimulator):
    start_epc = tag_generator.start_epc
    qtd = tag_generator.qtd

    try:
        base_value = int(start_epc, 16)
    except ValueError:
        return JSONResponse(
            content={"error": "EPC inválido, deve ser apenas hexadecimal"}, status_code=400
        )

    for i in range(qtd):
        epc_value = base_value + i
        epc_hex = f"{epc_value:024x}"
        await events.on_tag(
            {
                "device": tag_generator.device,
                "epc": epc_hex,
            }
        )

    return JSONResponse(content={"detail": f"{qtd} tags ok"})


@router.post(
    "/connection",
    responses=rfid_base_responses,
    summary="Simulate connection state",
    description="Simulates the connection state change for the specified device.",
)
async def simulator_connection(connection: BooleanDeviceRequest):
    try:
        if connection.state:
            await events.on_connect(connection.device)
            return {"msg": f"{connection.device} CONNECTED"}
        else:
            await events.on_disconnect(connection.device)
            return {"msg": f"{connection.device} DISCONNECTED"}
    except Exception as e:
        logging.error(f"Error while processing connection simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post(
    "/inventory",
    responses=rfid_base_responses,
    summary="Simulate inventory state",
    description="Starts or stops the inventory simulation for the specified device.",
)
async def simulator_inventory(inventory: BooleanDeviceRequest):
    try:
        if inventory.state:
            await events.on_start(inventory.device)
            return {"msg": f"{inventory.device} STARTED"}
        else:
            await events.on_stop(inventory.device)
            return {"msg": f"{inventory.device} STOPPED"}
    except Exception as e:
        logging.error(f"Error while processing inventory simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post(
    "/event",
    responses=rfid_base_responses,
    summary="Simulate an event",
    description="Simulate an event with a simulated data",
)
async def simulator_event(event: EventRequest):
    try:
        event_json = event.model_dump()
        msg = await events.on_event(**event_json)
        return {"msg": msg}
    except Exception as e:
        logging.error(f"Error while processing event simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
