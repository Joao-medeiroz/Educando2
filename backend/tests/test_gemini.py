from types import SimpleNamespace

from app import gemini_client, quota


class FakeModels:
    def __init__(self, resposta):
        self.resposta = resposta

    def generate_content(self, model, contents, config):
        self.ultima_config = config
        return self.resposta


def cliente_falso(resposta, monkeypatch):
    monkeypatch.setattr(gemini_client, "GEMINI_API_KEY", "chave-de-teste")
    cliente = SimpleNamespace(models=FakeModels(resposta))
    monkeypatch.setattr(gemini_client, "_cliente", cliente)
    return cliente


def setup_function():
    quota._estado.update({"dia": None, "chamadas": 0, "esgotado": False})


def test_pesquisa_extrai_texto_e_fontes_do_google(monkeypatch):
    resposta = SimpleNamespace(
        text="A FGV oferece vestibulares próprios.",
        candidates=[SimpleNamespace(grounding_metadata=SimpleNamespace(grounding_chunks=[
            SimpleNamespace(web=SimpleNamespace(uri="https://www.fgv.br/vestibular", title="FGV")),
            SimpleNamespace(web=SimpleNamespace(uri="https://www.fgv.br/vestibular", title="FGV repetida")),
            SimpleNamespace(web=None),
        ]))],
    )
    cliente = cliente_falso(resposta, monkeypatch)
    resultado = gemini_client.pesquisar_na_web("conhece a prova da FGV?", [])
    assert resultado["texto"].startswith("A FGV")
    assert resultado["fontes"] == [{"titulo": "FGV", "link": "https://www.fgv.br/vestibular"}]
    assert cliente.models.ultima_config.tools  # a ferramenta de busca foi enviada


def test_pesquisa_sem_metadados_nao_quebra(monkeypatch):
    cliente_falso(SimpleNamespace(text="Resposta simples.", candidates=[]), monkeypatch)
    resultado = gemini_client.pesquisar_na_web("pergunta", [])
    assert resultado == {"texto": "Resposta simples.", "fontes": []}


def test_chamada_conta_na_cota(monkeypatch):
    cliente_falso(SimpleNamespace(text="ok", candidates=[]), monkeypatch)
    gemini_client.pesquisar_na_web("pergunta", [])
    assert quota._estado["chamadas"] == 1


def test_erro_de_cota_da_pesquisa_nao_desliga_o_chat(monkeypatch):
    class FalhaNaBusca:
        def generate_content(self, **_):
            raise Exception("429 RESOURCE_EXHAUSTED: search quota")
    monkeypatch.setattr(gemini_client, "GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(gemini_client, "_cliente", SimpleNamespace(models=FalhaNaBusca()))
    try:
        gemini_client.pesquisar_na_web("como funciona a FGV?", [])
    except gemini_client.IAEsgotada:
        raise AssertionError("erro da pesquisa não deveria desligar o chat")
    except gemini_client.IAIndisponivel:
        pass
    assert quota._estado["esgotado"] is False


def test_busca_sem_texto_tenta_de_novo_sem_a_ferramenta(monkeypatch):
    chamadas = []

    class Modelos:
        def generate_content(self, model, contents, config):
            chamadas.append(config.tools)
            if config.tools:
                return SimpleNamespace(text=None, candidates=[SimpleNamespace(finish_reason="STOP",
                                                                              grounding_metadata=None)])
            return SimpleNamespace(text="A FGV costuma ter processo próprio; confira o edital.", candidates=[])
    monkeypatch.setattr(gemini_client, "GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(gemini_client, "_cliente", SimpleNamespace(models=Modelos()))
    resultado = gemini_client.pesquisar_na_web("como funciona a FGV?", [])
    assert resultado["texto"].startswith("A FGV")
    assert len(chamadas) == 2 and chamadas[0] and not chamadas[1]


def test_resposta_de_busca_nao_usa_mime_json(monkeypatch):
    cliente = cliente_falso(SimpleNamespace(text="ok", candidates=[]), monkeypatch)
    gemini_client.pesquisar_na_web("pergunta", [])
    assert cliente.models.ultima_config.response_mime_type is None
