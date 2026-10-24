"""Carrega a base de oportunidades (JSON exportado do JS) e faz a busca."""
import json
import unicodedata
from functools import lru_cache

from .config import DATA_PATH

CATEGORIAS = {
    "cursos": "Cursos, faculdades e cursinhos",
    "emprego": "Estágio, emprego e Jovem Aprendiz",
    "idiomas": "Idiomas",
    "intercambio": "Intercâmbio",
}


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparar 'estágio' com 'estagio'."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def carregar_base() -> tuple:
    """Lê o JSON uma vez por instância. Itens sem título ou link são descartados."""
    with open(DATA_PATH, encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    itens = []
    for categoria, lista in dados.get("itens", {}).items():
        if categoria not in CATEGORIAS:
            continue
        for item in lista:
            if not item.get("titulo") or not item.get("link"):
                continue
            itens.append({
                "categoria": categoria,
                "tipo": item.get("tipo", ""),
                "titulo": item["titulo"],
                "descricao": item.get("descricao", ""),
                "local": item.get("local", ""),
                "link": item["link"],
                "imagem": item.get("imagem", ""),
            })
    return tuple(itens)


def buscar(categoria=None, palavras=None, limite=4) -> list:
    """Filtra por categoria e ordena pelo número de palavras-chave encontradas."""
    resultados = [i for i in carregar_base() if categoria is None or i["categoria"] == categoria]

    termos = [normalizar(p) for p in (palavras or []) if p.strip()]
    if termos:
        pontuados = []
        for item in resultados:
            alvo = normalizar(f"{item['titulo']} {item['tipo']} {item['descricao']}")
            pontos = sum(1 for termo in termos if termo in alvo)
            if pontos > 0:
                pontuados.append((pontos, item))
        pontuados.sort(key=lambda par: -par[0])
        resultados = [item for _, item in pontuados]

    return resultados[:limite]
