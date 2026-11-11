from types import SimpleNamespace

import pytest

from app import gemini_client, quota


class Modelos:
    def __init__(self, texto):
        self.texto = texto
        self.config_recebida = None

    def generate_content(self, model, contents, config):
        self.config_recebida = config
        return SimpleNamespace(text=self.texto, candidates=[])


@pytest.fixture(autouse=True)
def estado_limpo(monkeypatch):
    quota._estado.update({"dia": None, "chamadas": 0, "esgotado": False})
    yield
    quota._estado.update({"dia": None, "chamadas": 0, "esgotado": False})


def cliente_falso(monkeypatch, texto):
    modelos = Modelos(texto)
    monkeypatch.setattr(gemini_client, "GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(gemini_client, "_cliente", SimpleNamespace(models=modelos))
    return modelos


def test_refinar_usa_os_trechos_sem_ferramenta_de_busca(monkeypatch):
    modelos = cliente_falso(monkeypatch, "A FGV tem inscrições online (FGV Vestibular).")
    resultados = [{"titulo": "FGV Vestibular", "link": "https://vestibular.fgv.br", "trecho": "Inscrições online."}]
    texto = gemini_client.refinar_resposta("como me inscrevo na fgv?", [], resultados)
    assert texto.startswith("A FGV")
    assert not modelos.config_recebida.tools
    assert modelos.config_recebida.response_mime_type is None


def test_sem_busca_responde_com_conhecimento_geral(monkeypatch):
    cliente_falso(monkeypatch, "Em linhas gerais, esses processos costumam ter prova e documentos.")
    assert gemini_client.responder_sem_busca("como funciona?", []).startswith("Em linhas gerais")


def test_chamadas_contam_na_cota(monkeypatch):
    cliente_falso(monkeypatch, "ok")
    gemini_client.responder_sem_busca("pergunta", [])
    assert quota._estado["chamadas"] == 1
