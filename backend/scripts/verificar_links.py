"""Verifica se os links oficiais cadastrados ainda respondem. Não usa IA e não gasta cota.

Uso (na pasta backend, com o ambiente virtual ativado):
    python scripts\\verificar_links.py

Mostra os links com problema (erro, página fora do ar ou redirecionamento estranho) para você revisar.
"""
import json
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVOS = [
    RAIZ / "data" / "recursos_oficiais.json",
    RAIZ / "data" / "guias.json",
    RAIZ / "data" / "oportunidades.json",
]
TIMEOUT = 10


def coletar_links():
    links = {}
    for arquivo in ARQUIVOS:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        for url, origem in _percorrer(dados, arquivo.name):
            if url.startswith("https://"):
                links.setdefault(url, origem)
    return links


def _percorrer(obj, origem):
    if isinstance(obj, dict):
        for chave, valor in obj.items():
            if chave == "link" and isinstance(valor, str):
                yield valor, origem
            else:
                yield from _percorrer(valor, origem)
    elif isinstance(obj, list):
        for item in obj:
            yield from _percorrer(item, origem)


def verificar(url):
    requisicao = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (verificador de links)"})
    try:
        with urllib.request.urlopen(requisicao, timeout=TIMEOUT) as resposta:
            return resposta.status, None
    except urllib.error.HTTPError as erro:
        return erro.code, None
    except Exception as erro:  # sem conexão, DNS, tempo esgotado...
        return None, type(erro).__name__


def main():
    links = coletar_links()
    print(f"Verificando {len(links)} links...\n")
    problemas = 0
    for url, origem in sorted(links.items()):
        status, erro = verificar(url)
        if status is not None and status < 400:
            continue
        problemas += 1
        motivo = f"HTTP {status}" if status else f"erro: {erro}"
        print(f"[{origem}] {motivo}\n    {url}\n")
    print("Tudo certo." if problemas == 0 else f"{problemas} link(s) para revisar.")


if __name__ == "__main__":
    main()
