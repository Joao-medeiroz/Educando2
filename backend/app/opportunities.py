"""Base de oportunidades do site e opções online curadas."""
import json
import unicodedata
from functools import lru_cache

from .config import DATA_PATH, RECURSOS_PATH

CATEGORIAS = {
    "cursos": "Cursos, faculdades e cursinhos",
    "emprego": "Estágio, emprego e Jovem Aprendiz",
    "idiomas": "Idiomas",
    "intercambio": "Intercâmbio",
}

# Palavras que não ajudam na busca. Sem isso, "de" ou "para" batem com quase qualquer descrição.
STOPWORDS = {
    "para", "pra", "tem", "uma", "uns", "umas", "que", "com", "sem", "sobre", "pode", "poderia",
    "quero", "queria", "gostaria", "saber", "minha", "meu", "estou", "sou", "ando", "procurando",
    "oportunidade", "oportunidades", "area", "ajuda", "ajudar", "encontrar", "alguma", "algum",
    "tudo", "bem", "oi", "ola", "voce", "vcs", "entre", "dos", "das", "nos", "nas",
    "pelo", "pela", "isso", "esse", "essa", "este", "esta", "mais", "muito", "tambem", "ainda",
    "acho", "boa", "bom", "pensando", "bastante", "gosto", "faculdade", "curso", "cursos",
}


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparar 'estágio' com 'estagio'."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def limpar_palavras(texto: str) -> list:
    """Remove pontuação, stopwords e palavras muito curtas."""
    texto = " ".join("".join(c if c.isalnum() else " " for c in normalizar(texto)).split())
    return [p for p in texto.split() if len(p) >= 3 and p not in STOPWORDS]


@lru_cache(maxsize=1)
def carregar_base() -> tuple:
    """Oportunidades do site. Lido uma vez por instância; itens sem título ou link são descartados."""
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
            })
    return tuple(itens)


def buscar(categoria=None, palavras=None, limite=2, geral_se_sem_match=False) -> list:
    """Filtra por categoria e ordena pelo número de palavras-chave encontradas.

    geral_se_sem_match: se nenhuma palavra bater, devolve os itens da categoria.
    Usar só quando o pedido já é claro pela categoria (regras). Para a IA, o padrão é
    não devolver nada, para não mostrar oportunidades sem relação com o pedido.
    """
    base = [i for i in carregar_base() if categoria is None or i["categoria"] == categoria]

    termos = [normalizar(p) for p in (palavras or []) if p.strip()]
    if not termos:
        return []

    pontuados = []
    for item in base:
        alvo = normalizar(f"{item['titulo']} {item['descricao']}")
        pontos = sum(1 for termo in termos if termo in alvo)
        if pontos > 0:
            pontuados.append((pontos, item))

    if pontuados:
        pontuados.sort(key=lambda par: -par[0])
        return [item for _, item in pontuados][:limite]
    return base[:limite] if geral_se_sem_match else []


def titulos_da_base() -> list:
    """Títulos das oportunidades do site. Usados pela IA para identificar a que foi citada na conversa."""
    return [i["titulo"] for i in carregar_base()]


def encontrar_por_titulo(titulo) -> dict | None:
    if not titulo:
        return None
    for item in carregar_base():
        if item["titulo"] == titulo:
            return item
    return None


@lru_cache(maxsize=1)
def carregar_recursos() -> dict:
    with open(RECURSOS_PATH, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def opcoes_online(categoria=None, palavras=None, limite=2) -> list:
    """Recursos oficiais curados, escolhidos pelo assunto (palavras) e/ou pela categoria.

    Sem categoria e sem palavras, não sugere nada. Com palavras, ordena pelo que bate com o assunto
    (título, descrição e tags). Se nada bater e houver categoria, mostra os recursos da categoria.
    """
    recursos_todos = carregar_recursos()
    if categoria:
        lista = list(recursos_todos.get(categoria, []))
    else:
        lista = [r for chave, rs in recursos_todos.items() if isinstance(rs, list) for r in rs]

    termos = [normalizar(p) for p in (palavras or []) if p.strip()]
    if not termos and categoria is None:
        return []
    if termos:
        pontuados = []
        for recurso in lista:
            alvo = normalizar(f"{recurso['titulo']} {recurso.get('descricao', '')} {' '.join(recurso.get('tags', []))}")
            pontos = sum(1 for termo in termos if termo in alvo)
            if pontos > 0:
                pontuados.append((pontos, recurso))
        if pontuados:
            pontuados.sort(key=lambda par: -par[0])
            lista = [recurso for _, recurso in pontuados]

    return [
        {"titulo": r["titulo"], "descricao": r.get("descricao", ""), "link": r["link"]}
        for r in lista[:limite]
        if str(r.get("link", "")).startswith("https://")
    ]
