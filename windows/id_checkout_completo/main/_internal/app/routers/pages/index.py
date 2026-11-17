from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core import settings, templates
from app import __version__
from app.services import rfid_manager

router = APIRouter(prefix='', tags=['Pages'])


@router.get('/', response_class=HTMLResponse)
async def index(request: Request):
	alerts = []
	if settings.TAG_PREFIX:
		alerts.append(
			{
				'text': f'Tag prefix is set: {settings.TAG_PREFIX}',
				'level': 'warning',
			}
		)
	# alerts example
	# alerts = [
	# 	{'text': 'Sistema SMARTX RFID iniciado com sucesso!', 'level': 'success'},
	# 	{'text': 'Conectado aos dispositivos RFID', 'level': 'info'},
	# 	{'text': 'Atenção: Verifique a configuração dos devices', 'level': 'warning'},
	# 	{'text': 'Erro de conexão detectado', 'level': 'error'},
	# ]
	if not rfid_manager.controller.operation:
		return RedirectResponse(url='/select_operation')
	return templates.TemplateResponse(
		'pages/index/main.html',
		{
			'request': request,
			'title': settings.TITLE,
			'alerts': alerts,
			'only_complete_table': settings.ONLY_COMPLETE_TABLE,
		},
		media_type='text/html; charset=utf-8',
	)


@router.get('/login', response_class=HTMLResponse)
async def login(request: Request):
	return templates.TemplateResponse(
		'pages/index/login.html',
		{'request': request, 'title': 'Login', 'alerts': [], 'include_header': False},
		media_type='text/html; charset=utf-8',
	)


@router.get('/select_operation', response_class=HTMLResponse)
async def select_operation(request: Request):
	return templates.TemplateResponse(
		'pages/index/select_operation.html',
		{'request': request, 'title': settings.TITLE, 'alerts': [], 'table': 'select_operation'},
		media_type='text/html; charset=utf-8',
	)


@router.get('/docs', response_class=HTMLResponse)
async def docs():
	return get_swagger_ui_html(
		openapi_url='/openapi.json',
		title=f'{settings.TITLE} v{__version__}',
		swagger_js_url='/static/docs/swagger-ui-bundle.js',
		swagger_css_url='/static/docs/swagger-ui.css',
		swagger_favicon_url='/static/images/logo.png',
	)


@router.get('/tag_details', response_class=HTMLResponse)
async def tag_details(request: Request):
	return templates.TemplateResponse(
		'pages/index/main.html',
		{'request': request, 'title': settings.TITLE, 'alerts': [], 'table': 'complete'},
		media_type='text/html; charset=utf-8',
	)


@router.get('/gtin', response_class=HTMLResponse)
async def gtin(request: Request):
	return templates.TemplateResponse(
		'pages/index/main.html',
		{'request': request, 'title': settings.TITLE, 'alerts': [], 'table': 'gtin'},
		media_type='text/html; charset=utf-8',
	)


@router.get('/by_ant', response_class=HTMLResponse)
async def by_ant(request: Request):
	return templates.TemplateResponse(
		'pages/index/main.html',
		{'request': request, 'title': settings.TITLE, 'alerts': [], 'table': 'by_ant'},
		media_type='text/html; charset=utf-8',
	)


@router.get('/license', response_class=HTMLResponse)
async def license(request: Request):
	return templates.TemplateResponse(
		'pages/license/main.html',
		{'request': request, 'title': 'License', 'alerts': []},
		media_type='text/html; charset=utf-8',
	)
