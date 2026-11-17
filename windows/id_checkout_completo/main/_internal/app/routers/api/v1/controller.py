from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse, RedirectResponse
from smartx_rfid.utils.path import get_prefix_from_path
from app.schemas.write_list import WriteListPrefixModel
from app.services import rfid_manager
from app.schemas.auth import AuthenticateModel

router_prefix = get_prefix_from_path(__file__)
router = APIRouter(prefix=router_prefix, tags=[router_prefix])


@router.get(
	'/controller_info',
	summary='Get RFID info',
)
async def controller_info():
	controller = rfid_manager.controller

	# Monta dict nome: tipo para atributos e métodos públicos
	info = {}
	for name in dir(controller):
		if name.startswith('_'):
			continue
		attr = getattr(controller, name)
		if callable(attr):
			info[name] = f'function ({type(attr).__name__})'
		else:
			info[name] = type(attr).__name__
	return info


# [WRITE LIST]
@router.get(
	'/get_write_list',
	summary='Get write list from RFID controller',
)
async def get_write_list():
	return rfid_manager.controller.write_list


@router.post(
	'/create_write_list_prefix',
	summary='Write a list of tags to the RFID controller',
)
async def create_write_list_prefix(write_list: WriteListPrefixModel):
	write_list = rfid_manager.controller.create_write_list_prefix(
		write_list.epcs, write_list.prefix
	)
	if not write_list:
		return JSONResponse(
			status_code=400, content={'message': 'Tags not found in current tag list'}
		)
	return write_list


@router.post(
	'/add_to_write_list/{tid}/{target}',
	summary='Add a tag to the write list in the RFID controller',
)
async def add_to_write_list(tid: str, target: str):
	tag = rfid_manager.controller.tags.get_by_identifier(tid.lower(), identifier_type='tid')
	if not tag:
		return JSONResponse(status_code=404, content={'message': f'Tag {tid} not found'})
	rfid_manager.controller.add_to_write_list(tag, target)
	return {'message': f'Tag {tid} added to write list with target {target} successfully'}


@router.post(
	'/clear_write_list',
	summary='Clear the write list in the RFID controller',
)
async def clear_write_list():
	rfid_manager.controller.clear_write_list()
	return {'message': 'Write list cleared successfully'}


@router.delete(
	'/delete_tid_from_write_list/{tid}',
	summary='Delete a tag from the write list in the RFID controller',
)
async def delete_tid_from_write_list(tid: str):
	tag = rfid_manager.controller.tags.get_by_identifier(tid.lower(), identifier_type='tid')
	if not tag:
		return JSONResponse(status_code=404, content={'message': f'Tag {tid} not found'})
	success = rfid_manager.controller.remove_from_write_list(tag)
	if success:
		return {'message': f'Tag {tid} removed from write list successfully'}
	else:
		return JSONResponse(
			status_code=400, content={'message': f'Failed to remove tag {tid} from write list'}
		)


# HELPER FUNCTIONS - Placeholder
@router.get(
	'/get_value_placeholder',
	summary='Get a value for placeholder',
)
async def get_value_placeholder():
	return {
		'suporte': rfid_manager.controller.support_data.support
		if rfid_manager.controller.support_data
		else None,
	}


@router.delete(
	'/delete_value_placeholder',
	summary='Delete the value for placeholder',
)
async def delete_value_placeholder():
	rfid_manager.controller.clear_support()
	return {'message': 'Value for placeholder deleted successfully'}


@router.post(
	'/set_value_placeholder/{value}',
	summary='Set a value for placeholder',
)
async def set_value_placeholder(value: str):
	try:
		rfid_manager.controller.set_support(value)
		return {'message': f'Suporte definido para {value} com sucesso'}
	except ValueError as e:
		return JSONResponse(status_code=400, content={'message': str(e)})


@router.post(
	'/set_single_support',
	summary='Set support and EAN for Single operation',
)
async def set_single_support(payload: dict = Body(...)):
	support = payload.get('support')
	ean = payload.get('ean')
	if not isinstance(support, str) or not isinstance(ean, str):
		return JSONResponse(status_code=400, content={'message': 'Informe o suporte e o EAN'})
	try:
		rfid_manager.controller.set_single_support(support, ean)
		return {'message': f'Suporte {support} e EAN definidos com sucesso'}
	except ValueError as e:
		return JSONResponse(status_code=400, content={'message': str(e)})


@router.post(
	'/receive_from_file',
	summary='Set values for placeholder from uploaded file',
)
async def receive_from_file(items: list[dict]):
	if not items:
		return JSONResponse(status_code=400, content={'message': 'Payload cannot be empty'})

	print(f'Received items from file: {items}')
	return {
		'message': 'Values received successfully',
		'received_count': len(items),
		'preview': items[:5],
	}


@router.post(
	'/authenticate',
	summary='Authenticate user',
)
async def authenticate(auth_data: AuthenticateModel = Body(...)):
	rfid_manager.controller.db_user = auth_data.username
	rfid_manager.controller.db_password = auth_data.password
	success, data = rfid_manager.controller.setup_as_400()
	if success:
		return JSONResponse(content={'message': 'Authentication successful'})
	else:
		rfid_manager.controller.db_user = None
		rfid_manager.controller.db_password = None
		return JSONResponse(content={'error': data}, status_code=401)


@router.post(
	'/logout',
	summary='Logout user',
)
async def logout():
	rfid_manager.controller.db_user = None
	rfid_manager.controller.db_password = None
	return RedirectResponse(url='/login', status_code=303)


@router.get(
	'/get_user',
	summary='Get current authenticated user',
)
async def get_user():
	return {'user': rfid_manager.controller.db_user}


# Operation management endpoints


@router.post(
	'/set_operation/{operation}',
	summary='Set the current operation',
)
async def set_operation(operation: str):
	try:
		rfid_manager.controller.set_operation(operation)
		return {'message': f'Operação definida para {operation} com sucesso'}
	except ValueError as e:
		return JSONResponse(status_code=400, content={'error': str(e)})


@router.get(
	'/get_operation',
	summary='Get the current operation',
)
async def get_operation():
	return {'operation': rfid_manager.controller.operation}


@router.delete(
	'/cancel_operation',
	summary='Delete the current operation',
)
async def cancel_operation():
	rfid_manager.controller.cancel_operation()
	return {'message': 'Operação removida com sucesso'}


@router.get(
	'/get_today_count',
	summary='Get the count for today',
)
async def get_today_count():
	return {'today_count': rfid_manager.controller.today_count}


@router.get(
	'/compare_tags',
	summary='Compare current tags with support data',
)
async def compare_tags():
	return rfid_manager.controller.compare_tags()


@router.get(
	'/can_finish',
	summary='Check if the current operation can be finished',
)
async def can_finish():
	return rfid_manager.controller.can_finish()


@router.post(
	'/finish',
	summary='Finish the current operation',
)
async def finish():
	try:
		rfid_manager.controller.finish()
		return {'message': 'Operação finalizada com sucesso'}
	except ValueError as e:
		return JSONResponse(status_code=400, content={'error': str(e)})


@router.get(
	'/get_epc_by_gtin/{gtin}',
	summary='Get EPC by GTIN',
)
async def get_epc_by_gtin(gtin: str):
	try:
		return {'epc': rfid_manager.controller.get_epc_by_gtin(gtin)}
	except ValueError as e:
		return JSONResponse(status_code=400, content={'error': str(e)})


@router.post(
	'/add_by_gtin/{gtin}',
	summary='Add a tag by GTIN',
)
async def add_by_gtin(gtin: str):
	try:
		epc = rfid_manager.controller.get_epc_by_gtin(gtin)
		simulated_tag = {
			'epc': epc,
			'tid': epc,
			'ant': 1,
			'rssi': -50,
		}
		rfid_manager.on_event(
			device=rfid_manager.build_device('SIMULATOR'),
			event_type='tag',
			event_data=simulated_tag,
		)
		return {'message': 'Tag adicionada com sucesso'}
	except ValueError as e:
		return JSONResponse(status_code=400, content={'error': str(e)})
