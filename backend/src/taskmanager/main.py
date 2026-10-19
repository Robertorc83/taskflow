"""ASGI entry point: `uvicorn taskmanager.main:app`."""

from taskmanager.presentation.app import create_app

app = create_app()
