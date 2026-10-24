"""Regras locais: resolvem saudações e buscas simples sem chamar a IA (sem gastar tokens)."""
import re

from .opportunities import CATEGORIAS, limpar_palavras, normalizar

SAUDACOES = {"oi", "ola", "bom dia", "boa tarde", "boa noite", "e ai", "eae"}

# Termos que indicam cada categoria (já sem acento).
TERMOS_POR_CATEGORIA = {
    "emprego": ["estagio", "estagiar", "emprego", "vaga", "trabalho", "aprendiz", "carreira"],
    "cursos": ["curso", "cursinho", "faculdade", "enem", "prouni", "sisu", "fies", "universidade", "graduacao", "bolsa"],
    "idiomas": ["idioma", "ingles", "espanhol", "frances", "lingua"],
    "intercambio": ["intercambio", "exterior", "internacional", "estudar fora"],
}

TEXTO_SAUDACAO = "Oi, tudo bem? Eu sou o Edu, assistente do Educando. Você está precisando de alguma oportunidade?"
TEXTO_SEM_CATEGORIA = "Posso te ajudar com cursos, estágios e vagas, idiomas ou intercâmbio. Sobre qual deles você quer saber?"
TEXTO_PERFIL = (
    "Que bom que você está explorando! Me conta um pouquinho: você está no ensino médio, na faculdade "
    "ou já se formou?"
)
TEXTO_DIRECIONAR = (
    "Me conta um pouco mais sobre o que você gosta e sobre sua situação atual, assim consigo indicar "
    "caminhos mais certeiros."
)
TEXTO_DETALHE = "Aqui estão os detalhes que temos no Educando sobre essa oportunidade:"
TEXTO_FALLBACK = (
    "Não consegui entender sua mensagem agora. Tente falar de cursos, estágios e vagas, "
    "idiomas ou intercâmbio."
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
        return {"intencao": "busca", "categoria": encontradas[0], "palavras": limpar_palavras(mensagem)}
    if len(encontradas) > 1:
        return {"intencao": "busca", "categoria": None, "palavras": limpar_palavras(mensagem)}

    return {"intencao": "desconhecida"}


NOME_PLURAL = {
    "cursos": "cursos e faculdades",
    "emprego": "estágios e vagas",
    "idiomas": "cursos de idiomas",
    "intercambio": "intercâmbios",
}


def _opcoes(quantidade: int) -> str:
    return "opção" if quantidade == 1 else "opções"


def texto_com_resultados(categoria, quantidade: int) -> str:
    """Texto padrão para os cards. Só é usado se a IA não estiver disponível."""
    if categoria is None:
        return f"Encontrei {quantidade} {_opcoes(quantidade)} que podem te interessar. Dá uma olhada:"
    return f"Encontrei {quantidade} {_opcoes(quantidade)} em {NOME_PLURAL[categoria]}. Dá uma olhada:"


def texto_sem_resultados(categoria, tem_online: bool = False) -> str:
    """Texto padrão sem resultados no site. Só é usado se a IA não estiver disponível."""
    onde = "" if categoria is None else f" em {NOME_PLURAL[categoria]}"
    if tem_online:
        return f"Ainda não tenho oportunidades cadastradas{onde} no Educando, mas encontrei estas opções online:"
    return f"Ainda não tenho oportunidades cadastradas{onde} no Educando."
