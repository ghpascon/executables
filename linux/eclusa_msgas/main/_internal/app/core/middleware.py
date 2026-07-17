import inspect
import sys
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.gzip import GZipMiddleware


# =====================
#  AUTO-REGISTRATION
# =====================

def setup_middlewares(app):
    """Automatically register all BaseHTTPMiddleware subclasses defined in this module"""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Auto-register custom middlewares
    current_module = sys.modules[__name__]
    for name, obj in inspect.getmembers(current_module, inspect.isclass):
        if issubclass(obj, BaseHTTPMiddleware) and obj is not BaseHTTPMiddleware:
            app.add_middleware(obj)
            print(f"[Middleware] Registered: {name}")

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    Instrumentator().instrument(app).expose(app, include_in_schema=False)

