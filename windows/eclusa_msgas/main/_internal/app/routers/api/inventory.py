import logging
from typing import List, Union

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse

from app.core.path import get_prefix_from_path
from app.schemas.devices import validate_device
from app.schemas.responses import device_responses
from app.services.devices import devices
from app.services.events import events
from app.schemas.tag import TagSchema

router = APIRouter(prefix=get_prefix_from_path(__file__), tags=[get_prefix_from_path(__file__)])


@router.post("/start/{device}")
async def start_inventory(device: str):
    try:
        status, msg = validate_device(device=device)
        if not status:
            logging.error(f"[ START ] {msg}")
            raise HTTPException(status_code=422, detail=msg)

        logging.info(f"START -> {device}")
        await devices.start_inventory(device)
        return {"msg": msg}

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"msg": e})


@router.post("/stop/{device}")
async def stop_inventory(device: str):
    try:
        status, msg = validate_device(device=device)
        if not status:
            logging.error(f"[ STOP ] {msg}")
            raise HTTPException(status_code=422, detail=msg)

        logging.info(f"STOP -> {device}")
        await devices.stop_inventory(device)
        return {"msg": msg}

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"msg": e})


@router.get(
    "/get_tags",
    summary="Get Current RFID Tags",
    description="Retrieve all currently detected RFID tags from all connected readers",
    response_description="List of RFID tag objects with their metadata",
)
async def get_tags():
    return [tag for tag in events.tags.values()]


@router.get(
    "/get_tags_count",
    summary="Get Current Tags Count",
    description="Return the number of currently detected RFID tags from all connected readers",
    response_description='{"count": tag_count}',
)
async def get_tags_count():
    return {"count": len(events.tags)}


@router.get(
    "/get_epcs",
    summary="Get EPCs of Current Tags",
    description="Retrieve the EPCs of all currently detected RFID tags",
    response_description="List of EPC strings",
)
async def get_epcs():
    return [tag.get("epc") for tag in events.tags.values() if tag.get("epc") is not None]

@router.get(
    "/get_gtin_count",
    summary="Get GTIN counts",
    description="Returns the count of tags by GTIN. Tags without GTIN are labeled 'NC'.",
    response_description="List of GTINs with their counts",
)
async def get_gtin_count():
    eans = {}
    for tag in events.tags.values():
        ean = tag.get("gtin") or "NC"
        eans[ean] = eans.get(ean, 0) + 1
    return [{"gtin": k, "count": v} for k, v in eans.items()]


@router.post(
    "/receive_tags",
    summary="Receive tags from external devices",
    description="Receives either a single tag or a list of tags",
)
async def receive_tags(tags: Union[TagSchema, List[TagSchema]] = Body(...)):
    tags = tags if isinstance(tags, list) else [tags]
    for tag in tags:
        try:
            await events.on_tag(tag.model_dump())
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return {"msg": "success"}


@router.post("/clear/{device}")
async def clear_tags(device: str):
    logging.info(f"CLEAR -> {device}")
    await devices.clear_tags(device)
    return {"msg": f"{device} clear tags"}


@router.post(
    "/clear_all_tags",
    responses=device_responses,
    summary="Clear tags from all devices",
    description="Clears the tag lists from all connected devices.",
)
async def clear_all_tags():
    try:
        await devices.clear_tags()
        return {"msg": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/any_reading",
    summary="Check if any reader is reading",
    description="Returns whether any reader is actively scanning for tags.",
)
async def any_reading():
    for device in devices.devices.values():
        if device.is_reading:
            return {"is_reading": 1}
    return {"is_reading": 0}
