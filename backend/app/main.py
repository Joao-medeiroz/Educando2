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
import re
from contextvars import ContextVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from . import agente, config, guias, opportunities, pesquisa_web, quota, rules
from .config import ALLOWED_ORIGINS, RATE_LIMIT_POR_MINUTO
from .gemini_client import (
    IAEsgotada,
    IAIndisponivel,
    compor_resposta_com_ia,
    interpretar_com_ia,
    refinar_resposta,
    responder_sem_busca,
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


# Perfil da pessoa desta requisição e o que a conversa acabou de revelar (por contexto, sem estado global).
_perfil_atual = ContextVar("perfil_atual", default=None)
_perfil_extraido = ContextVar("perfil_extraido", default=None)


URL_RE = re.compile(r"(?:https?://|www\.)[^\s)\]\"']+")


def _chave_url(url) -> str:
    """Compara endereços sem esquema, sem www. e sem barra final."""
    limpo = re.sub(r"^https?://", "", str(url).strip().lower())
    limpo = re.sub(r"^www\.", "", limpo)
    return limpo.rstrip("/")


def _filtrar_urls(texto, permitidos):
    """Só mantém endereços que vieram dos dados; qualquer outro é removido.

    Links em markdown, [texto](endereço), são reduzidos ao texto quando o endereço não é permitido.
    """
    chaves = {_chave_url(p) for p in permitidos}
    markdown = re.compile(r"\[([^\]]+)\]\(\s*([^)\s]+)\s*\)")
    texto = markdown.sub(lambda m: m.group(0) if _chave_url(m.group(2)) in chaves else m.group(1), texto)
    return URL_RE.sub(lambda m: m.group(0) if _chave_url(m.group(0)) in chaves else "", texto)


def _links_permitidos(itens, online, referencias, guia) -> set:
    links = {i["link"] for i in itens} | {o["link"] for o in online} | {r["link"] for r in referencias}
    if guia:
        links |= {f["link"] for f in guia["fontes"]}
    links |= {l.link for l in _links_do_site()}
    return links


def _redigir(mensagem, historico, tarefa, padrao, itens=(), online=(), detalhe=None, guia=None,
             referencias=None) -> str:
    """Pede à IA a resposta do Edu. Se ela não responder, usa o texto padrão.
    Se a cota acabou (IAEsgotada), o erro sobe até o endpoint, que desliga o chat."""
    try:
        texto = compor_resposta_com_ia(mensagem, historico, tarefa, itens, online, detalhe, guia,
                                       referencias=referencias, perfil=_perfil_atual.get())
        return _filtrar_urls(texto, _links_permitidos(itens, online, referencias or [], guia))
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
    """Busca na web (Tavily) e o Gemini organiza os trechos encontrados. Sem resultados, o Gemini
    responde com o conhecimento geral, sem inventar links nem datas."""
    try:
        resultados = pesquisa_web.pesquisar(mensagem)
    except pesquisa_web.PesquisaIndisponivel:
        resultados = []

    if resultados:
        try:
            texto = refinar_resposta(mensagem, historico, resultados)
        except IAEsgotada:
            raise
        except IAIndisponivel:
            texto = rules.TEXTO_PESQUISA_FALHOU
        fontes = [OpcaoOnline(titulo=r["titulo"], descricao="Saiba mais", link=r["link"]) for r in resultados]
        return ChatResponse(texto=texto, opcoes_online=fontes, origem="web")

    try:
        texto = responder_sem_busca(mensagem, historico)
    except IAEsgotada:
        raise
    except IAIndisponivel:
        texto = rules.TEXTO_PESQUISA_FALHOU
    return ChatResponse(texto=texto, origem="ia")


def _links_do_site() -> list:
    """Páginas do próprio Educando, para a pessoa explorar as oportunidades cadastradas."""
    return [OpcaoOnline(titulo="Oportunidades no Educando", descricao="Tudo o que cadastramos para você",
                        link=f"{config.SITE_URL}/oportunidades.html")]


def _perguntas_do_edu(historico) -> int:
    return sum(1 for turno in historico if turno["papel"] == "edu" and "?" in turno["texto"])


def _orientar(mensagem, historico, explicito: bool) -> ChatResponse:
    """Conversa com orientação. Se a pessoa pediu uma indicação, responde já, com referências da web."""
    if not explicito:
        texto = _redigir(mensagem, historico, "orientar", rules.TEXTO_CONVERSA)
        return ChatResponse(texto=texto, opcoes_online=_links_do_site(), origem="ia")

    contexto = " ".join(t["texto"] for t in historico if t["papel"] == "usuario")[-300:]
    try:
        referencias = pesquisa_web.pesquisar(f"{contexto} {mensagem}".strip())
    except pesquisa_web.PesquisaIndisponivel:
        referencias = []
    texto = _redigir(mensagem, historico, "orientar_pedido", rules.TEXTO_CONVERSA, referencias=referencias)
    opcoes = [OpcaoOnline(titulo=r["titulo"], descricao="Saiba mais", link=r["link"]) for r in referencias]
    return ChatResponse(texto=texto, opcoes_online=opcoes + _links_do_site(), origem="ia")


MAXIMO_LINKS = 4  # links visíveis por resposta (no texto, nos cards e nas opções somados)
MARKDOWN_RE = re.compile(r"\[([^\]]+)\]\(\s*((?:https?://|www\.)[^)\s]+)\s*\)")


def _limitar_links_no_texto(texto):
    """Mantém no texto no máximo MAXIMO_LINKS endereços distintos. Devolve o texto e quantos ficaram."""
    usados = set()

    def markdown(m):
        chave = _chave_url(m.group(2))
        if chave in usados or len(usados) < MAXIMO_LINKS:
            usados.add(chave)
            return m.group(0)
        return m.group(1)

    def solto(m):
        chave = _chave_url(m.group(0))
        if chave in usados or len(usados) < MAXIMO_LINKS:
            usados.add(chave)
            return m.group(0)
        return ""

    texto = MARKDOWN_RE.sub(markdown, texto)
    texto = URL_RE.sub(solto, texto)
    return texto, len(usados)


def _resposta_do_agente(mensagem, resultado) -> ChatResponse:
    """Monta a resposta do agente: só endereços vindos das ferramentas podem aparecer no texto."""
    _perfil_extraido.set(resultado["perfil"])
    permitidos = {f["link"] for f in resultado["fontes"]} | {o["link"] for o in resultado["oportunidades"]}
    permitidos |= {l.link for l in _links_do_site()}
    texto = _filtrar_urls(resultado["texto"], permitidos)
    texto, no_texto = _limitar_links_no_texto(texto)
    vagas = MAXIMO_LINKS - no_texto
    cards = [Oportunidade(**o) for o in resultado["oportunidades"]][:vagas]
    vagas -= len(cards)
    links_cards = {o["link"] for o in resultado["oportunidades"]}
    opcoes = [OpcaoOnline(titulo=f["titulo"][:80], descricao="Saiba mais", link=f["link"])
              for f in resultado["fontes"] if f["link"] not in links_cards]
    opcoes = (opcoes + _links_do_site())[:max(vagas, 0)]
    return ChatResponse(texto=texto, oportunidades=cards, opcoes_online=opcoes, origem="agente")


def _responder(corpo: ChatRequest, request: Request) -> ChatResponse:
    _limitar_frequencia(request)

    mensagem = corpo.mensagem.strip()
    if not mensagem:
        raise HTTPException(status_code=422, detail="Mensagem vazia.")
    historico = [{"papel": t.papel, "texto": t.texto} for t in corpo.historico]

    info = rules.interpretar(mensagem)

    if info["intencao"] == "saudacao":
        return ChatResponse(texto=rules.TEXTO_SAUDACAO, origem="regras")

    if config.AGENTE_ATIVO:
        try:
            resultado = agente.responder(mensagem, historico, _perfil_atual.get() or {})
        except IAEsgotada:
            raise
        except Exception as erro:
            # Se o agente falhar, a resposta cai nas regras antigas (plano B), sem quebrar a conversa.
            print("Usando regras antigas:", type(erro).__name__)
            resultado = None
        if resultado:
            return _resposta_do_agente(mensagem, resultado)

    if info["intencao"] == "desconhecida":
        try:
            ia = interpretar_com_ia(mensagem, historico, opportunities.titulos_da_base())
        except IAEsgotada:
            raise
        except IAIndisponivel:
            # Não entendemos a intenção: em vez de desistir, tentamos responder pela busca.
            return _pesquisar(mensagem, historico)

        if ia["intencao"] in ("perfil", "direcionar", "conversar") and (
            ia.get("pedido_explicito") or _perguntas_do_edu(historico) >= 2
        ):
            # Pedido explícito: responde já. Conversa que já fez perguntas suficientes: dá caminhos concretos.
            return _orientar(mensagem, historico, explicito=ia.get("pedido_explicito", False))

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

        _perfil_extraido.set(ia.get("perfil_extraido", {}))
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
        if not online:
            # A base não tem nada sobre o assunto: procura na web em vez de responder vazio.
            return _pesquisar(mensagem, historico)
        texto = _redigir(mensagem, historico, "recomendar",
                         rules.texto_sem_resultados(categoria, tem_online=bool(online)),
                         online=online)
        online = online + [{"titulo": x.titulo, "descricao": x.descricao, "link": x.link}
                           for x in _links_do_site()]

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
    from .gemini_client import limpar_perfil
    token_perfil = _perfil_atual.set(limpar_perfil(corpo.perfil))
    token_extraido = _perfil_extraido.set({})
    try:
        resposta = _responder(corpo, request)
        resposta.perfil_atualizado = _perfil_extraido.get() or {}
        return resposta
    except IAEsgotada:
        return ChatResponse(texto=rules.TEXTO_ESGOTADO, origem="fallback", chat_indisponivel=True)
    finally:
        _perfil_atual.reset(token_perfil)
        _perfil_extraido.reset(token_extraido)
