"""Regras locais: resolvem saudações e buscas simples sem chamar a IA."""
import re

from .opportunities import CATEGORIAS, normalizar

SAUDACOES = {"oi", "ola", "bom dia", "boa tarde", "boa noite", "e ai", "eae"}

# Termos que indicam cada categoria (já sem acento).
TERMOS_POR_CATEGORIA = {
    "emprego": ["estagio", "estagiar", "emprego", "vaga", "trabalho", "aprendiz", "carreira"],
    "cursos": ["curso", "cursinho", "faculdade", "enem", "prouni", "sisu", "fies", "universidade", "graduacao", "bolsa"],
    "idiomas": ["idioma", "ingles", "espanhol", "frances", "lingua"],
    "intercambio": ["intercambio", "exterior", "internacional", "estudar fora"],
}

TEXTO_SAUDACAO = (
    "Olá! Sou o assistente do Educando. Posso buscar cursos, faculdades, estágios e vagas, "
    "idiomas e intercâmbios. O que você está procurando?"
)
TEXTO_FALLBACK = (
    "No momento não consigo interpretar sua mensagem com a ajuda da IA. "
    "Tente escrever uma categoria: cursos, emprego, idiomas ou intercâmbio."
)
TEXTO_SEM_CATEGORIA = (
    "Posso ajudar com cursos, estágios e vagas, idiomas ou intercâmbio. Sobre qual deles você quer saber?"
)


def interpretar(mensagem: str) -> dict:
    """Devolve a intenção identificada por regras: 'saudacao', 'busca' ou 'desconhecida'."""
    # Remove pontuação e espaços extras: "oi, tudo bem?" -> "oi tudo bem"
    texto = " ".join(re.sub(r"[^a-z0-9 ]", " ", normalizar(mensagem)).split())
    palavras = texto.split()

    if texto in SAUDACOES or (len(palavras) <= 3 and palavras and palavras[0] in {"oi", "ola"}):
        return {"intencao": "saudacao"}

    encontradas = [
        categoria
        for categoria, termos in TERMOS_POR_CATEGORIA.items()
        if any(termo in texto for termo in termos)
    ]
    if len(encontradas) == 1:
        return {"intencao": "busca", "categoria": encontradas[0], "palavras": palavras}
    if len(encontradas) > 1:
        # Mais de uma categoria: busca em todas (sem filtrar categoria).
        return {"intencao": "busca", "categoria": None, "palavras": palavras}

    return {"intencao": "desconhecida"}


def montar_texto_busca(categoria, quantidade: int) -> str:
    if quantidade == 0:
        return "Não encontrei oportunidades para essa busca. Tente outras palavras ou uma categoria diferente."
    if categoria is None:
        return f"Encontrei {quantidade} oportunidade(s) que combinam com sua busca:"
    return f"Encontrei {quantidade} oportunidade(s) em {CATEGORIAS[categoria]}:"
