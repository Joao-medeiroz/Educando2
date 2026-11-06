"""Endpoints da API do Edu.

Fluxo de cada mensagem:
1. Validação e limite de frequência.
2. Saudação: resposta fixa, sem IA.
3. Regras locais identificam categoria e palavras. Quando não bastam, a IA entende a mensagem
   no contexto e escolhe a intenção (1ª chamada): pedido, perfil, direcionar, detalhar ou tutorial.
4. Conforme a intenção:
   - tutorial: responde com o guia revisado do projeto (sem busca na web).
   - detalhar: explica a oportunidade citada com todos os dados da base.
   - perfil: faz uma pergunta para conhecer a pessoa.
   - direcionar: sugere caminhos e mostra o que existe no site.
   - pedido: mostra oportunidades do site e opções online curadas.
5. A IA redige a resposta (2ª chamada). Se a cota acabar, o chat é desligado (chat_indisponivel).
"""
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from . import guias, opportunities, quota, rules
from .config import ALLOWED_ORIGINS, RATE_LIMIT_POR_MINUTO
from .gemini_client import (
    IAEsgotada,
    IAIndisponivel,
    compor_resposta_com_ia,
    interpretar_com_ia,
    pesquisar_na_web,
)
from .schemas import ChatRequest, ChatResponse, OpcaoOnline, Oportunidade

LIMITE_CARDS = 2  # oportunidades do site por resposta
LIMITE_ONLINE = 2  # opções online por resposta

app = FastAPI(title="Educando - Edu", docs_url=None, redoc_url=None, openapi_url=None)

# Sem origens configuradas, nenhuma origem cruzada é aceita. Em produção o front e a API
# ficam no mesmo domínio, então CORS não é necessário.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
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


def _redigir(mensagem, historico, tarefa, padrao, itens=(), online=(), detalhe=None, guia=None) -> str:
    """Pede à IA a resposta do Edu. Se ela não responder, usa o texto padrão.
    Se a cota acabou (IAEsgotada), o erro sobe até o endpoint, que desliga o chat."""
    try:
        return compor_resposta_com_ia(mensagem, historico, tarefa, itens, online, detalhe, guia)
    except IAEsgotada:
        raise
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


def _pesquisar(mensagem, historico) -> ChatResponse:
    """Pesquisa na web com a ferramenta do Google. A própria resposta da pesquisa vai para o chat
    (uma chamada só, para economizar cota), com as fontes que o Google informou."""
    try:
        resultado = pesquisar_na_web(mensagem, historico)
    except IAEsgotada:
        raise
    except IAIndisponivel:
        return ChatResponse(texto=rules.TEXTO_PESQUISA_FALHOU, origem="fallback")
    fontes = [OpcaoOnline(titulo=f["titulo"][:80], descricao="Encontrado na web. Confira os detalhes no site.",
                          link=f["link"]) for f in resultado["fontes"]]
    return ChatResponse(texto=resultado["texto"], opcoes_online=fontes, origem="web")


def _responder(corpo: ChatRequest, request: Request) -> ChatResponse:
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
        except IAEsgotada:
            raise
        except IAIndisponivel:
            return ChatResponse(texto=rules.TEXTO_FALLBACK, origem="fallback")

        if ia["intencao"] == "conversar":
            texto = _redigir(mensagem, historico, "conversar", rules.TEXTO_CONVERSA)
            return ChatResponse(texto=texto, origem="ia")

        if ia["intencao"] == "tutorial":
            guia = guias.buscar_guia(ia["palavras"])
            if guia:
                texto = _redigir(mensagem, historico, "guia", rules.TEXTO_GUIA, guia=guia)
                fontes = [OpcaoOnline(titulo=f["titulo"], descricao="Fonte oficial", link=f["link"])
                          for f in guia["fontes"]]
                return ChatResponse(texto=texto, opcoes_online=fontes, origem="ia")
            # Sem guia revisado: pesquisa na web, em vez de inventar um passo a passo.
            return _pesquisar(mensagem, historico)

        if ia["intencao"] == "pesquisar":
            # Se a base tiver algo sobre o assunto, mostra a base; senão, pesquisa na web.
            if not opportunities.tem_titulo_relacionado(ia["palavras"]):
                return _pesquisar(mensagem, historico)
            ia = {**ia, "intencao": "pedido"}

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
            # Nesta etapa a conversa vem antes das recomendações: sem cards nem opções online.
            texto = _redigir(mensagem, historico, "direcionar", rules.TEXTO_DIRECIONAR)
            return ChatResponse(texto=texto, origem="ia", categoria=ia["categoria"])

        if ia["intencao"] == "pedido" and not ia["categoria"] and not ia["palavras"]:
            return ChatResponse(texto=rules.TEXTO_CONVERSA, origem="ia")

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


@app.get("/api/saude")
def saude():
    return {"status": "ok"}


@app.get("/api/status")
def status():
    """O front consulta isto ao abrir a página: se a cota acabou, o botão do chat não aparece."""
    return {"disponivel": quota.disponivel()}


@app.post("/api/chat", response_model=ChatResponse)
def chat(corpo: ChatRequest, request: Request):
    try:
        return _responder(corpo, request)
    except IAEsgotada:
        return ChatResponse(texto=rules.TEXTO_ESGOTADO, origem="fallback", chat_indisponivel=True)
