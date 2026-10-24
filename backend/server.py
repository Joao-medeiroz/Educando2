"""Ponto de entrada usado pela Vercel e pelo uvicorn: `uvicorn server:app` (dentro de backend/)."""
from app.main import app  # noqa: F401
