"""Endpoint do chatbot. Coordena: validação -> regras -> IA (se necessário) -> busca -> resposta."""
import time
from collections import defaultdict, deque
from .config import GEMINI_MODEL
from .gemini_client import _obter_cliente

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from . import opportunities, rules
from .config import ALLOWED_ORIGINS, MAX_OPORTUNIDADES, RATE_LIMIT_POR_MINUTO
from .gemini_client import IAIndisponivel, interpretar_com_ia
from .schemas import ChatRequest, ChatResponse, Oportunidade

app = FastAPI(title="Educando - Chatbot", docs_url=None, redoc_url=None, openapi_url=None)

# Sem origens configuradas, nenhuma origem cruzada é aceita. Em produção o front e a API
# ficam no mesmo domínio, então CORS não é necessário.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

# Limite por IP em memória. Limitação: cada instância tem sua própria contagem.
_historico_ips = defaultdict(deque)


def _limitar_frequencia(request: Request) -> None:
    encaminhado = request.headers.get("x-forwarded-for", "")
    ip = encaminhado.split(",")[0].strip() or (request.client.host if request.client else "desconhecido")

    agora = time.time()
    if len(_historico_ips) > 10_000:
        _historico_ips.clear()  # evita crescimento infinito da memória
    fila = _historico_ips[ip]
    while fila and agora - fila[0] > 60:
        fila.popleft()
    if len(fila) >= RATE_LIMIT_POR_MINUTO:
        raise HTTPException(status_code=429, detail="Muitas mensagens em pouco tempo. Aguarde um minuto.")
    fila.append(agora)


def _para_oportunidades(itens: list) -> list:
    return [Oportunidade(**item) for item in itens]


@app.get("/api/saude")
def saude():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(corpo: ChatRequest, request: Request):
    _limitar_frequencia(request)

    mensagem = corpo.mensagem.strip()
    if not mensagem:
        raise HTTPException(status_code=422, detail="Mensagem vazia.")

    info = rules.interpretar(mensagem)
    origem = "regras"

    if info["intencao"] == "saudacao":
        return ChatResponse(texto=rules.TEXTO_SAUDACAO, origem=origem)

    if info["intencao"] == "desconhecida":
        try:
            ia = interpretar_com_ia(mensagem)
        except IAIndisponivel:
            return ChatResponse(texto=rules.TEXTO_FALLBACK, origem="fallback")
        info = {"intencao": "busca", "categoria": ia["categoria"], "palavras": ia["palavras"]}
        origem = "ia"
        if info["categoria"] is None and not info["palavras"]:
            return ChatResponse(texto=rules.TEXTO_SEM_CATEGORIA, origem=origem)

    itens = opportunities.buscar(info["categoria"], info["palavras"], MAX_OPORTUNIDADES)
    return ChatResponse(
        texto=rules.montar_texto_busca(info["categoria"], len(itens)),
        oportunidades=_para_oportunidades(itens),
        origem=origem,
        categoria=info["categoria"],
    )
