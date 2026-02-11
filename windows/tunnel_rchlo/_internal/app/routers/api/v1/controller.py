from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.services import rfid_manager
from smartx_rfid.utils.path import get_prefix_from_path
from fastapi import Request

router_prefix = get_prefix_from_path(__file__)
router = APIRouter(prefix=router_prefix, tags=[router_prefix])


@router.post('/inform_box')
async def inform_box(request: Request):
	data = await request.json()
	box_info = data.get('box_info')
	rfid_manager.controller.update_box_info(box_info)
	return JSONResponse(content={'box_info': box_info})


@router.get('/box_info')
async def get_box_info():
	return JSONResponse(content=rfid_manager.controller.box_info)
