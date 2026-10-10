"""ASGI entry point: `uvicorn p3d_api.main:app`."""

from .app import create_app

app = create_app()
