"""Busca na web pelo Tavily (plano gratuito de 1.000 créditos por mês, sem cartão).

O Tavily devolve títulos, endereços e trechos das páginas. O Gemini, em seguida, organiza esses
trechos numa resposta (ver gemini_client.refinar_resposta). Assim, a informação vem da web real,
e o Gemini só reescreve o que foi encontrado.
"""
import datetime
import os
import time

from .config import LIMITE_PESQUISAS_MES
from .opportunities import STOPWORDS, normalizar

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
CACHE_SEGUNDOS = 24 * 60 * 60
_cache = {}
_contagem = {"mes": None, "n": 0}


PALAVRAS_GENERICAS = STOPWORDS | {
    "brasil", "melhor", "melhores", "qual", "quais", "onde", "pode", "posso", "saber", "inscrever", "inscreve",
    "inscrevo", "fazer", "precisa", "preciso", "vestibular", "processo", "como", "para", "uma", "quero",
}


DOMINIOS_IGNORADOS = ("instagram.com", "facebook.com", "youtube.com", "tiktok.com", "x.com", "twitter.com",
                      "linkedin.com", "pinterest.com")


def _dominio_ignorado(link: str) -> bool:
    return any(d in link for d in DOMINIOS_IGNORADOS)


def termos_distintivos(pergunta: str) -> list:
    """Palavras que identificam o assunto (nomes de instituições, provas, cursos)."""
    texto = " ".join("".join(c if c.isalnum() else " " for c in normalizar(pergunta)).split())
    return [p for p in texto.split() if len(p) >= 3 and p not in PALAVRAS_GENERICAS]


def montar_consulta(pergunta: str) -> str:
    """Acrescenta o contexto do Brasil e pede o site oficial, para o Tavily trazer páginas certas."""
    return f"{pergunta.strip()} Brasil site oficial"


def _relevantes(resultados: list, pergunta: str) -> list:
    termos = termos_distintivos(pergunta)
    if not termos:
        return []  # sem termos do assunto, nenhum resultado é confiável
    return [r for r in resultados if any(t in normalizar(r["titulo"] + " " + r["trecho"]) for t in termos)]


class PesquisaIndisponivel(Exception):
    """A busca não pôde ser feita (sem chave, limite do mês atingido ou erro do serviço)."""


def _atualizar_mes():
    mes = datetime.date.today().strftime("%Y-%m")
    if _contagem["mes"] != mes:
        _contagem.update({"mes": mes, "n": 0})


def disponivel() -> bool:
    _atualizar_mes()
    return bool(TAVILY_API_KEY) and _contagem["n"] < LIMITE_PESQUISAS_MES


def pesquisar(consulta: str, max_resultados: int = 4) -> list:
    """Devolve até max_resultados itens: {titulo, link, trecho}. Só links https."""
    chave = " ".join(consulta.lower().split())
    em_cache = _cache.get(chave)
    if em_cache and time.time() - em_cache["quando"] < CACHE_SEGUNDOS:
        return em_cache["resultados"]

    if not disponivel():
        raise PesquisaIndisponivel("sem chave ou limite mensal atingido")

    try:
        from tavily import TavilyClient
        _atualizar_mes()
        _contagem["n"] += 1
        resposta = TavilyClient(api_key=TAVILY_API_KEY).search(
            query=montar_consulta(consulta), search_depth="basic", max_results=max_resultados
        )
    except Exception as erro:
        # Sem chave, endereço ou detalhes da chave nos logs: só o tipo do erro.
        print("Tavily falhou:", type(erro).__name__)
        raise PesquisaIndisponivel(type(erro).__name__) from None

    resultados, vistos = [], set()
    for item in resposta.get("results", []):
        link = str(item.get("url", ""))
        if not link.startswith("https://") or link in vistos or _dominio_ignorado(link):
            continue
        vistos.add(link)
        resultados.append({
            "titulo": (item.get("title") or "Página encontrada na web")[:120],
            "link": link,
            "trecho": (item.get("content") or "")[:600],
        })
        if len(resultados) == max_resultados:
            break

    resultados = _relevantes(resultados, consulta)
    _cache[chave] = {"quando": time.time(), "resultados": resultados}
    if len(_cache) > 200:
        _cache.clear()
    return resultados
