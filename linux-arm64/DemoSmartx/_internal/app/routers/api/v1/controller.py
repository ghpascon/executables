from fastapi import APIRouter
from fastapi.responses import JSONResponse
from smartx_rfid.utils.path import get_prefix_from_path
from app.schemas.controller import OrderSchema

from app.services import rfid_manager

router_prefix = get_prefix_from_path(__file__)
router = APIRouter(prefix=router_prefix, tags=[router_prefix])


@router.post(
	'/add_orders',
	summary='Add multiple orders',
)
async def add_orders(orders: OrderSchema | list[OrderSchema]):
	success, message = rfid_manager.controller.add_orders(
		orders.model_dump()
		if isinstance(orders, OrderSchema)
		else [order.model_dump() for order in orders]
	)
	return JSONResponse(
		status_code=200 if success else 400,
		content={'message': message},
	)


@router.get(
	'/get_orders',
	summary='Get all orders',
)
async def get_orders():
	orders = rfid_manager.controller.get_orders()
	return JSONResponse(
		status_code=200,
		content={'orders': orders},
	)


@router.post(
	'/set_order',
)
async def set_order(order: dict):
	order_data = rfid_manager.controller.get_order(order_id=order.get('order'))
	rfid_manager.controller.set_order(order_data)
	return JSONResponse(
		status_code=200,
		content={'message': f'Order set to {order.get("order")}'},
	)


@router.get(
	'/get_order',
)
async def get_order():
	return JSONResponse(
		status_code=200,
		content={'order': rfid_manager.controller.order_data.get('order')},
	)


@router.get(
	'/get_comparison',
)
async def get_comparison():
	return JSONResponse(status_code=200, content=rfid_manager.controller.get_comparison())


@router.post(
	'/finish_order',
)
async def finish_order():
	success, message = rfid_manager.controller.finish_order()
	return JSONResponse(
		status_code=200 if success else 400,
		content={'message': message},
	)
