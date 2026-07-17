import asyncio
import logging
from typing import List, Union

from fastapi import APIRouter, Body, Request

from app.core.path import get_prefix_from_path
from app.db.database import database_engine
from app.schemas.events import EventRequest
from app.services.events import events

router = APIRouter(prefix=get_prefix_from_path(__file__), tags=[get_prefix_from_path(__file__)])


@router.get(
    "/get_events",
    summary="Get Recent Events",
    description="Retrieve the most recent system events and logs",
    response_description="List of recent event objects",
)
async def get_events():
    return list(events.events)


@router.post(
    "/receive_events",
    summary="Receive events from external devices",
    description="Receives either a single event or a list of events",
)
async def receive_events(
    events_received: Union[EventRequest, List[EventRequest]] = Body(...),
):
    events_received = events_received if isinstance(events_received, list) else [events_received]
    logging.info(events_received)
    for event in events_received:
        event = event.model_dump()
        asyncio.create_task(events.on_event(**event))
    return {"msg": "success"}


@router.get(
    "/get_report",
    summary="Get report",
    description="Retrieves the current report generated from database records.",
    response_description="Report object",
)
async def get_report(request: Request):
    return await database_engine.get_report()
