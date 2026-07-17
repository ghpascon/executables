from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.core.settings import settings
from app.core.templates import templates

router = APIRouter(prefix="", tags=["Pages"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index/main.html",
        {"request": request, "title": settings.data.get("TITLE", "SMARTX")},
        media_type="text/html; charset=utf-8",
    )

@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    return templates.TemplateResponse(
        "users/main.html",
        {"request": request, "title": "Gerenciar Usuários"},
        media_type="text/html; charset=utf-8",
    )

@router.get("/docs", include_in_schema=False)
async def docs():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=settings.data.get("TITLE", "SMARTX") + " - Docs",
        swagger_js_url="/static/docs/swagger-ui-bundle.js",
        swagger_css_url="/static/docs/swagger-ui.css",
        swagger_favicon_url="/static/images/logo.png",
    )
