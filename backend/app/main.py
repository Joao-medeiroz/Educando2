"""Endpoints da API do Edu.

Fluxo de cada mensagem:
1. Validação e limite de frequência.
2. Saudação: resposta fixa, sem IA.
3. Regras locais identificam categoria e palavras. Quando não bastam, a IA entende a mensagem
   no contexto e escolhe a intenção (1ª chamada): pedido, perfil, direcionar ou detalhar.
4. Conforme a intenção:
   - detalhar: explica a oportunidade citada com todos os dados da base.
   - perfil: faz uma pergunta para conhecer a pessoa, sem recomendar.
   - direcionar: faz perguntas ou sugere caminhos, e mostra o que existe no site.
   - pedido: mostra oportunidades do site e opções online curadas.
5. A IA redige a resposta (2ª chamada), só com essas listas. Se ela estiver indisponível,
   vai um texto padrão e os cards continuam aparecendo.
"""
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from . import opportunities, rules
from .config import ALLOWED_ORIGINS, RATE_LIMIT_POR_MINUTO
from .gemini_client import IAIndisponivel, compor_resposta_com_ia, interpretar_com_ia
from .schemas import ChatRequest, ChatResponse, OpcaoOnline, Oportunidade

LIMITE_CARDS = 2  # oportunidades do site por resposta
LIMITE_ONLINE = 2  # opções online por resposta

app = FastAPI(title="Educando - Edu", docs_url=None, redoc_url=None, openapi_url=None)

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


def _redigir(mensagem, historico, tarefa, padrao, itens=(), online=(), detalhe=None) -> str:
    """Pede à IA a resposta do Edu. Se ela não responder, usa o texto padrão."""
    try:
        return compor_resposta_com_ia(mensagem, historico, tarefa, itens, online, detalhe)
    except IAIndisponivel:
        return padrao


def _opcoes_online(categoria, palavras, itens) -> list:
    links_do_site = {i["link"] for i in itens}
    opcoes = opportunities.opcoes_online(categoria, palavras, limite=LIMITE_ONLINE + 2)
    return [o for o in opcoes if o["link"] not in links_do_site][:LIMITE_ONLINE]


def _detalhe(item) -> dict:
    """Dados que a IA pode usar para explicar a oportunidade (sem o link, que vai no botão)."""
    return {
        "titulo": item["titulo"],
        "tipo": item.get("tipo", ""),
        "local": item.get("local", ""),
        "categoria": item["categoria"],
        "descricao": item["descricao"],
    }


@app.get("/api/saude")
def saude():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(corpo: ChatRequest, request: Request):
    _limitar_frequencia(request)

    mensagem = corpo.mensagem.strip()
    if not mensagem:
        raise HTTPException(status_code=422, detail="Mensagem vazia.")
    historico = [{"papel": t.papel, "texto": t.texto} for t in corpo.historico]

    info = rules.interpretar(mensagem)

    if info["intencao"] == "saudacao":
        return ChatResponse(texto=rules.TEXTO_SAUDACAO, origem="regras")

    if info["intencao"] == "desconhecida":
        try:
            ia = interpretar_com_ia(mensagem, historico, opportunities.titulos_da_base())
        except IAIndisponivel:
            return ChatResponse(texto=rules.TEXTO_FALLBACK, origem="fallback")

        if ia["intencao"] == "detalhar" and ia["oportunidade"]:
            item = opportunities.encontrar_por_titulo(ia["oportunidade"])
            if item:
                texto = _redigir(mensagem, historico, "detalhar", rules.TEXTO_DETALHE,
                                 itens=[item], detalhe=_detalhe(item))
                return ChatResponse(
                    texto=texto,
                    oportunidades=[Oportunidade(**item)],
                    origem="ia",
                    categoria=item["categoria"],
                )

        if ia["intencao"] == "perfil":
            texto = _redigir(mensagem, historico, "perguntar_perfil", rules.TEXTO_PERFIL)
            return ChatResponse(texto=texto, origem="ia")

        if ia["intencao"] == "direcionar":
            itens = []
            if ia["categoria"] or ia["palavras"]:
                itens = opportunities.buscar(ia["categoria"], ia["palavras"], limite=LIMITE_CARDS)
            online = _opcoes_online(ia["categoria"], ia["palavras"], itens)
            texto = _redigir(mensagem, historico, "direcionar", rules.TEXTO_DIRECIONAR,
                             itens=itens, online=online)
            return ChatResponse(
                texto=texto,
                oportunidades=[Oportunidade(**item) for item in itens],
                opcoes_online=[OpcaoOnline(**o) for o in online],
                origem="ia",
                categoria=ia["categoria"],
            )

        info = {"categoria": ia["categoria"], "palavras": ia["palavras"]}
        origem, geral = "ia", False  # pedido vindo da IA: só mostra o que bate com as palavras
    else:
        origem, geral = "regras", True  # categoria clara por regras

    categoria, palavras = info["categoria"], info["palavras"]
    itens = []
    if categoria or palavras:
        itens = opportunities.buscar(categoria, palavras, limite=LIMITE_CARDS, geral_se_sem_match=geral)
    online = _opcoes_online(categoria, palavras, itens)

    if itens:
        texto = _redigir(mensagem, historico, "recomendar", rules.texto_com_resultados(categoria, len(itens)),
                         itens=itens, online=online)
    else:
        texto = _redigir(mensagem, historico, "recomendar",
                         rules.texto_sem_resultados(categoria, tem_online=bool(online)),
                         online=online)

    return ChatResponse(
        texto=texto,
        oportunidades=[Oportunidade(**item) for item in itens],
        opcoes_online=[OpcaoOnline(**o) for o in online],
        origem=origem,
        categoria=categoria,
    )
