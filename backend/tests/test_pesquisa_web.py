import pytest

from app import pesquisa_web


class ClienteFalso:
    chamadas = []

    def __init__(self, api_key):
        self.api_key = api_key

    def search(self, query, search_depth, max_results):
        ClienteFalso.chamadas.append(query)
        return {"results": [
            {"title": "FGV Vestibular", "url": "https://vestibular.fgv.br", "content": "Inscrições online."},
            {"title": "Repetida", "url": "https://vestibular.fgv.br", "content": "Duplicada."},
            {"title": "Sem https", "url": "http://insegura.example", "content": "Não usar."},
            {"title": "Edital", "url": "https://www.fgv.br/edital", "content": "Edital e datas."},
        ]}


@pytest.fixture(autouse=True)
def estado(monkeypatch):
    monkeypatch.setattr(pesquisa_web, "TAVILY_API_KEY", "chave-de-teste")
    monkeypatch.setattr(pesquisa_web, "_cache", {})
    monkeypatch.setattr(pesquisa_web, "_contagem", {"mes": None, "n": 0})
    ClienteFalso.chamadas = []
    monkeypatch.setattr("tavily.TavilyClient", ClienteFalso, raising=False)
    yield


def test_sem_chave_nao_pesquisa(monkeypatch):
    monkeypatch.setattr(pesquisa_web, "TAVILY_API_KEY", "")
    assert pesquisa_web.disponivel() is False
    with pytest.raises(pesquisa_web.PesquisaIndisponivel):
        pesquisa_web.pesquisar("fgv")


def test_resultados_so_https_e_sem_repeticao():
    resultados = pesquisa_web.pesquisar("como se inscreve na fgv")
    assert [r["link"] for r in resultados] == ["https://vestibular.fgv.br"]
    assert all("trecho" in r and "titulo" in r for r in resultados)


def test_resultado_repetido_nao_gasta_nova_busca():
    pesquisa_web.pesquisar("fgv inscricao")
    pesquisa_web.pesquisar("FGV   inscricao")
    assert len(ClienteFalso.chamadas) == 1


def test_limite_mensal_bloqueia_novas_buscas(monkeypatch):
    monkeypatch.setattr(pesquisa_web, "LIMITE_PESQUISAS_MES", 1)
    pesquisa_web.pesquisar("primeira")
    with pytest.raises(pesquisa_web.PesquisaIndisponivel):
        pesquisa_web.pesquisar("segunda")
