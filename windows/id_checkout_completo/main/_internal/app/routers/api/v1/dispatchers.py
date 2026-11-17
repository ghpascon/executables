from fastapi import APIRouter, Body
from smartx_rfid.utils.path import get_prefix_from_path

from app.services import rfid_manager

router_prefix = get_prefix_from_path(__file__)
router = APIRouter(prefix=router_prefix, tags=[router_prefix])


@router.get(
	'/get_dispatches_examples',
)
async def get_dispatches_examples():
	return rfid_manager.controller.dispatcher.get_example_names()


@router.get(
	'/get_example_dispatch/{dispatch_name}',
)
async def get_example_dispatch(dispatch_name: str):
	return rfid_manager.controller.dispatcher.get_example_content(dispatch_name)


@router.get(
	'/get_dispatches',
)
async def get_dispatches():
	return rfid_manager.controller.dispatcher.get_dispatch_names()


@router.get(
	'/get_dispatch/{dispatch_name}',
)
async def get_dispatch(dispatch_name: str):
	return rfid_manager.controller.dispatcher.get_dispatch_content(dispatch_name)


# This route creates or overwrites a dispatch with the provided content. The content should be a dict with the dispatch configuration.
@router.post(
	'/add_dispatch/{dispatch_name}',
)
async def add_dispatch(dispatch_name: str, content: dict = Body(...)):
	return rfid_manager.controller.dispatcher.create_dispatch(
		dispatch_name, content, overwrite=True
	)


@router.delete(
	'/delete_dispatch/{dispatch_name}',
)
async def delete_dispatch(dispatch_name: str):
	return rfid_manager.controller.dispatcher.delete_dispatch(dispatch_name)
