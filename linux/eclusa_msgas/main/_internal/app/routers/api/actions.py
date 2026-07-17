from fastapi import APIRouter, HTTPException

from app.core.settings import settings
from app.core.path import get_prefix_from_path
from app.schemas.events import ActionsRequest
from app.schemas.responses import rfid_actions_responses
from app.services.events import events

router_prefix = get_prefix_from_path(__file__)
router = APIRouter(prefix=router_prefix, tags=[router_prefix])


@router.get(
    "/get_actions_example",
    responses=rfid_actions_responses,
    summary="Get an example of RFID actions",
    description="Returns an example of RFID actions for all connected devices.",
)
async def get_actions_example():
    try:
        return await events.get_actions_example()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/get_actions",
    responses=rfid_actions_responses,
    summary="Get current RFID actions",
    description="Returns the list of currently configured RFID actions for all connected devices.",
)
async def get_actions():
    """
    Retrieve the currently configured actions for the RFID system.
    """
    try:
        return events.actions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/set_actions",
    responses=rfid_actions_responses,
    summary="Set RFID actions",
    description="Sets or updates the configured RFID actions and reloads application settings.",
)
async def set_actions(data: ActionsRequest):
    """
    Set new RFID actions using the provided request data.
    Reloads the system settings after applying the configuration.
    """
    try:
        data = data.model_dump()
        await events.set_actions(data)
        settings.load()
        return {"msg": "success", "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
