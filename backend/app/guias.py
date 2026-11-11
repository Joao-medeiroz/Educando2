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
    return tuple(
        g for g in dados.get("guias", [])
        if g.get("id") and g.get("titulo") and g.get("texto") and g.get("fontes")
    )


def buscar_guia(palavras=None) -> dict | None:
    """Devolve um guia só se ele cobrir TODAS as palavras específicas da pergunta.

    Se a pergunta cita algo que o guia não cobre (ex.: outra instituição), não há guia: a
    resposta deve vir da pesquisa na web. Guias são apoio, não uma regra fechada.
    """
    ignorar = TERMOS_GERAIS | STOPWORDS
    especificas = [normalizar(p) for p in (palavras or []) if p.strip() and normalizar(p) not in ignorar]
    if not especificas:
        return None
    for guia in carregar_guias():
        alvo = normalizar(f"{guia['titulo']} {' '.join(guia.get('tags', []))}")
        if all(termo in alvo for termo in especificas):
            return {
                "id": guia["id"],
                "titulo": guia["titulo"],
                "texto": guia["texto"][:LIMITE_TEXTO_GUIA],
                "fontes": guia["fontes"],
            }
    return None
