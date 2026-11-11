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
RATE_LIMIT_POR_MINUTO = int(os.getenv("RATE_LIMIT_POR_MINUTO", "20"))

RECURSOS_PATH = BASE_DIR / "data" / "recursos_oficiais.json"

GUIAS_PATH = BASE_DIR / "data" / "guias.json"
# Teto de chamadas ao Gemini por dia (o limite gratuito do modelo é 500). Folga para testes e picos.
LIMITE_DIARIO_IA = int(os.getenv("LIMITE_DIARIO_IA", "480"))  # plano gratuito do Gemini: 500 por dia

# Buscas na web por mês (plano gratuito do Tavily: 1.000). Folga de segurança.
LIMITE_PESQUISAS_MES = int(os.getenv("LIMITE_PESQUISAS_MES", "1000"))  # plano gratuito do Tavily

# Endereço do próprio site, usado nos links para as páginas do Educando.
SITE_URL = os.getenv("SITE_URL", "https://educando-rose.vercel.app").rstrip("/")

# Arquitetura de agente com ferramentas (padrão de mercado). Desligue com AGENTE_ATIVO=false para usar as regras antigas.
AGENTE_ATIVO = os.getenv("AGENTE_ATIVO", "true").lower() == "true"
