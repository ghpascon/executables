import asyncio
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from smartx_rfid.utils.path import get_prefix_from_path
from app.async_func.xtrack import update_tables
from app.services.xtrack import xtrack_manager

router_prefix = get_prefix_from_path(__file__)
router = APIRouter(prefix=router_prefix, tags=[router_prefix])


@router.get('/xtrack_info', summary='Get Xtrack integration info')
async def get_xtrack_info():
	success, info = await asyncio.to_thread(xtrack_manager.get_info)
	if success:
		return JSONResponse(info)
	else:
		return JSONResponse(content={'status': 'error', 'message': info}, status_code=500)


@router.post('/xtrack_update', summary='Trigger Xtrack data update')
async def trigger_xtrack_update():
	update_tables()
	return JSONResponse(content={'status': 'update triggered'})
