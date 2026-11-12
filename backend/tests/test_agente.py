import json

import pytest

from app import agente, main
from app.gemini_client import IAEsgotada


@pytest.fixture(autouse=True)
def limpo(monkeypatch):
    monkeypatch.setattr(main.config, "AGENTE_ATIVO", True)
    agente._fontes.set([])
    agente._oportunidades.set([])
    agente._perfil.set({})


def test_consultar_base_registra_as_oportunidades_e_as_fontes():
    saida = json.loads(agente.consultar_base("emprego", "estagio"))
    assert saida and all(o["link"].startswith("https://") for o in saida)
    assert agente._oportunidades.get() == saida
    assert {f["link"] for f in agente._fontes.get()} >= {o["link"] for o in saida}


def test_atualizar_perfil_aceita_so_campos_permitidos():
    assert agente.atualizar_perfil("area_interesse", "dados") == "Registrado."
    assert agente.atualizar_perfil("cpf", "123") == "Campo não aceito."
    assert agente._perfil.get() == {"area_interesse": "dados"}


def test_pesquisa_indisponivel_avisa_sem_quebrar(monkeypatch):
    monkeypatch.setattr(agente.pesquisa_web, "disponivel", lambda: False)
    assert agente.pesquisar_na_web("fgv").startswith("Pesquisa indisponível")


def test_guia_do_enem_traz_as_fontes_oficiais():
    saida = json.loads(agente.consultar_guia("enem inscricao"))
    assert saida["fontes"] and saida["fontes"][0]["link"].startswith("https://")


def test_resposta_do_agente_remove_links_inventados(monkeypatch):
    resultado = {
        "texto": "Confira em https://www.gov.br/inep/pt-br ou em https://site-inventado.example.",
        "fontes": [{"titulo": "Inep", "link": "https://www.gov.br/inep/pt-br", "trecho": "x"}],
        "oportunidades": [],
        "perfil": {"area_interesse": "saúde"},
    }
    monkeypatch.setattr(agente, "responder", lambda *a, **k: resultado)
    from fastapi.testclient import TestClient
    resposta = TestClient(main.app).post("/api/chat", json={"mensagem": "preparar para o enem"}).json()
    assert resposta["origem"] == "agente"
    assert "gov.br/inep" in resposta["texto"] and "site-inventado" not in resposta["texto"]
    assert resposta["perfil_atualizado"] == {"area_interesse": "saúde"}


def test_falha_do_agente_cai_nas_regras_antigas(monkeypatch):
    def falha(*a, **k):
        raise RuntimeError("falha qualquer")
    monkeypatch.setattr(agente, "responder", falha)
    monkeypatch.setattr(main, "interpretar_com_ia", lambda m, h, t: {"intencao": "conversar", "categoria": None,
                                                                     "palavras": [], "oportunidade": None,
                                                                     "pedido_explicito": False,
                                                                     "perfil_extraido": {}})
    monkeypatch.setattr(main, "compor_resposta_com_ia", lambda *a, **k: "Conversa pelas regras antigas.")
    from fastapi.testclient import TestClient
    resposta = TestClient(main.app).post("/api/chat", json={"mensagem": "estou pensando"}).json()
    assert resposta["texto"] == "Conversa pelas regras antigas."


def test_cota_esgotada_no_agente_desliga_o_chat(monkeypatch):
    def esgotada(*a, **k):
        raise IAEsgotada("LIMITE_DIARIO")
    monkeypatch.setattr(agente, "responder", esgotada)
    from fastapi.testclient import TestClient
    resposta = TestClient(main.app).post("/api/chat", json={"mensagem": "quero ajuda"}).json()
    assert resposta["chat_indisponivel"] is True



def test_buscar_vagas_abertas_usa_a_pesquisa_e_registra_as_fontes(monkeypatch):
    chamadas = []
    monkeypatch.setattr(agente.pesquisa_web, "disponivel", lambda: True)
    monkeypatch.setattr(agente.pesquisa_web, "pesquisar", lambda c: chamadas.append(c) or [
        {"titulo": "Vaga júnior de marketing", "link": "https://www.vagas.com.br/vaga-1", "trecho": "Inscrições até 30/11."}])
    saida = agente.buscar_vagas_abertas("marketing", "júnior")
    assert "marketing" in chamadas[0] and "júnior" in chamadas[0]
    assert "Inscrições até 30/11" in saida
    assert {f["link"] for f in agente._fontes.get()} == {"https://www.vagas.com.br/vaga-1"}



def test_botao_cursos_nao_traz_estagio(monkeypatch):
    saida = json.loads(agente.consultar_base("cursos", "faculdades"))
    assert all(o["categoria"] == "cursos" for o in saida)


def test_sinonimo_de_categoria_e_normalizado():
    saida = json.loads(agente.consultar_base("estágio", "marketing"))
    assert all(o["categoria"] == "emprego" for o in saida)


def test_guia_devolve_so_a_secao_pedida():
    resultado = json.loads(agente.consultar_guia("fuvest calendario"))
    secoes = [t["secao"] for t in resultado["trechos"]]
    assert "Calendário 2027" in secoes
    assert sum(len(t["texto"]) for t in resultado["trechos"]) <= 2400


def test_guia_de_programacao_pede_conferencia():
    resultado = json.loads(agente.consultar_guia("programacao python"))
    assert resultado["atencao"] is True
