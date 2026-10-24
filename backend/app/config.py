"""Configurações lidas de variáveis de ambiente (nunca valores fixos de segredos)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "oportunidades.json"

# Chave do Gemini: somente no back-end, via variável de ambiente.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Modelo configurável: os nomes e limites do Gemini mudam; confira em ai.google.dev.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Origens permitidas para CORS (vazio = nenhuma). Ex.: "http://localhost:5500"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]

MAX_MENSAGEM_CHARS = 500
MAX_OPORTUNIDADES = 4
RATE_LIMIT_POR_MINUTO = int(os.getenv("RATE_LIMIT_POR_MINUTO", "10"))

RECURSOS_PATH = BASE_DIR / "data" / "recursos_oficiais.json"
