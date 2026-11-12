"""Guias curtos e revisados, usados para responder tutoriais sem consultar a web."""
import json
from functools import lru_cache

from .config import GUIAS_PATH
from .opportunities import STOPWORDS, normalizar

LIMITE_TEXTO_GUIA = 2000  # caracteres enviados ao Gemini por guia: controla o consumo de tokens

# Palavras que aparecem em muitos guias. Sozinhas, não indicam que o guia responde a pergunta.
TERMOS_GERAIS = {
    "inscricao", "inscrever", "documento", "documentos", "prazo", "prazos", "isencao", "taxa",
    "prova", "curso", "cursos", "vaga", "vagas", "emprego", "trabalho", "faculdade", "universidade",
    "bolsa", "bolsas", "cadastro", "cadastrar", "perfil", "curriculo", "gov", "govbr", "brasil",
}


@lru_cache(maxsize=1)
def carregar_guias() -> tuple:
    with open(GUIAS_PATH, encoding="utf-8") as arquivo:
        dados = json.load(arquivo)
    validos = []
    for g in dados.get("guias", []):
        if not (g.get("id") and g.get("titulo") and g.get("fontes")):
            continue
        if not (g.get("texto") or g.get("secoes")):
            continue
        if not g.get("texto"):
            g["texto"] = " ".join(sec["texto"] for sec in g["secoes"])  # resumo para a busca antiga
        validos.append(g)
    return tuple(validos)


def buscar_guia(palavras=None) -> dict | None:
    """Devolve o guia que cobre TODAS as palavras específicas da pergunta (o de mais termos em comum).

    Se a pergunta cita algo que o guia não cobre (ex.: outra instituição), não há guia.
    """
    ignorar = TERMOS_GERAIS | STOPWORDS
    especificas = [normalizar(p) for p in (palavras or []) if p.strip() and normalizar(p) not in ignorar]
    if not especificas:
        return None
    melhor, melhor_pontos = None, -1
    for guia in carregar_guias():
        titulo = normalizar(guia["titulo"])
        alvo = normalizar(f"{guia['titulo']} {' '.join(guia.get('tags', []))}")
        if all(termo in alvo for termo in especificas):
            # Termo no título vale mais do que termo só nas tags.
            pontos = sum(2 if termo in titulo else 1 for termo in especificas)
            if pontos > melhor_pontos:
                melhor, melhor_pontos = guia, pontos
    if melhor is None:
        return None
    return {
        "id": melhor["id"],
        "titulo": melhor["titulo"],
        "texto": melhor["texto"][:LIMITE_TEXTO_GUIA],
        "fontes": melhor["fontes"],
    }


ORCAMENTO_TRECHOS = 2400  # caracteres de guia enviados ao modelo por consulta


def buscar_trechos(palavras=None, limite=3) -> dict:
    """Devolve só as seções que respondem à pergunta, com o orçamento de caracteres do modelo.

    Cada guia é dividido em seções; cada seção tem suas próprias tags. Assim o modelo recebe
    o trecho certo (ex.: a seção de calendário), e não o guia inteiro.
    """
    ignorar = TERMOS_GERAIS | STOPWORDS
    especificas = [normalizar(p) for p in (palavras or []) if p.strip() and normalizar(p) not in ignorar]
    if not especificas:
        return {"trechos": [], "fontes": [], "atencao": False}
    candidatos = []
    for guia in carregar_guias():
        tags_guia = normalizar(f"{guia['titulo']} {' '.join(guia.get('tags', []))}")
        secoes = guia.get("secoes") or [{"titulo": guia["titulo"], "tags": [], "texto": guia["texto"]}]
        for secao in secoes:
            alvo = normalizar(f"{tags_guia} {secao['titulo']} {' '.join(secao.get('tags', []))}")
            pontos = sum(1 for termo in especificas if termo in alvo)
            if pontos:
                candidatos.append((pontos, guia, secao))
    candidatos.sort(key=lambda c: -c[0])
    trechos, fontes, usados, total = [], [], set(), 0
    atencao = False
    for _, guia, secao in candidatos[:limite]:
        chave = (guia["id"], secao["titulo"])
        if chave in usados:
            continue
        texto = secao["texto"]
        if total + len(texto) > ORCAMENTO_TRECHOS:
            texto = texto[: max(0, ORCAMENTO_TRECHOS - total)]
        if not texto:
            break
        usados.add(chave)
        total += len(texto)
        trechos.append({"guia": guia["titulo"], "secao": secao["titulo"], "texto": texto})
        if guia.get("status") == "a_verificar":
            atencao = True
        for f in guia["fontes"]:
            if f not in fontes:
                fontes.append(f)
    return {"trechos": trechos, "fontes": fontes, "atencao": atencao}
