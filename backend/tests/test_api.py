import pytest
from fastapi.testclient import TestClient

from app import main, opportunities, quota, rules
from app.gemini_client import IAEsgotada, IAIndisponivel

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def estado_limpo():
    main._historico_ips.clear()
    quota._estado.update({"dia": None, "chamadas": 0, "esgotado": False})
    yield
    quota._estado.update({"dia": None, "chamadas": 0, "esgotado": False})


def classificacao(monkeypatch, intencao="pedido", categoria=None, palavras=(), oportunidade=None):
    chamadas = []

    def fake(mensagem, historico, titulos):
        chamadas.append((mensagem, historico, titulos))
        return {"intencao": intencao, "categoria": categoria, "palavras": list(palavras),
                "oportunidade": oportunidade}
    monkeypatch.setattr(main, "interpretar_com_ia", fake)
    return chamadas


def redacao(monkeypatch, texto="Texto redigido pela IA"):
    chamadas = []

    def fake(mensagem, historico, tarefa, itens=(), online=(), detalhe=None, guia=None, pesquisa=None):
        chamadas.append({"tarefa": tarefa, "itens": list(itens), "online": list(online), "detalhe": detalhe})
        return texto
    monkeypatch.setattr(main, "compor_resposta_com_ia", fake)
    return chamadas


def pesquisa(monkeypatch, texto="Resposta encontrada na web", fontes=None):
    chamadas = []
    fontes = fontes if fontes is not None else [{"titulo": "FGV", "link": "https://www.fgv.br"}]

    def fake(pergunta, historico):
        chamadas.append(pergunta)
        return {"texto": texto, "fontes": fontes}
    monkeypatch.setattr(main, "pesquisar_na_web", fake)
    return chamadas


def sem_classificacao(monkeypatch):
    def proibida(*_):
        raise AssertionError("a classificação pela IA não deveria rodar")
    monkeypatch.setattr(main, "interpretar_com_ia", proibida)


def test_saude():
    assert client.get("/api/saude").json() == {"status": "ok"}


def test_saudacao_nao_chama_ia(monkeypatch):
    sem_classificacao(monkeypatch)
    resposta = client.post("/api/chat", json={"mensagem": "Olá"}).json()
    assert resposta["origem"] == "regras"
    assert "Edu" in resposta["texto"]


def test_pedido_explicito_mostra_cards(monkeypatch):
    classificacao(monkeypatch, intencao="pedido", categoria="emprego", palavras=["estagio"])
    chamadas = redacao(monkeypatch)
    resposta = client.post("/api/chat", json={"mensagem": "quero ver estágios"}).json()
    assert resposta["oportunidades"]
    assert chamadas[0]["tarefa"] == "recomendar"


def test_cards_trazem_tipo_local_e_link(monkeypatch):
    classificacao(monkeypatch, intencao="pedido", categoria="emprego", palavras=["estagio"])
    redacao(monkeypatch)
    resposta = client.post("/api/chat", json={"mensagem": "quero ver estágios"}).json()
    for o in resposta["oportunidades"]:
        assert o["titulo"] and o["descricao"]
        assert o["link"].startswith("https://")


def test_resposta_separa_site_e_opcoes_online(monkeypatch):
    classificacao(monkeypatch, intencao="pedido", categoria="emprego", palavras=["estagio"])
    redacao(monkeypatch)
    resposta = client.post("/api/chat", json={"mensagem": "quero ver estágios"}).json()
    links_site = {o["link"] for o in resposta["oportunidades"]}
    assert all(o["link"] not in links_site for o in resposta["opcoes_online"])


def test_curso_solto_nao_dispara_recomendacoes(monkeypatch):
    classificacao(monkeypatch, intencao="conversar")
    chamadas = redacao(monkeypatch, "Você está pensando em estudar? Me conta mais.")
    resposta = client.post("/api/chat", json={"mensagem": "curso"}).json()
    assert resposta["oportunidades"] == [] and resposta["opcoes_online"] == []
    assert chamadas[0]["tarefa"] == "conversar"


def test_detalhar_usa_os_dados_completos_da_oportunidade(monkeypatch):
    titulo = opportunities.carregar_base()[0]["titulo"]
    classificacao(monkeypatch, intencao="detalhar", oportunidade=titulo)
    chamadas = redacao(monkeypatch, "Explicação detalhada")
    resposta = client.post("/api/chat", json={
        "mensagem": "me explica melhor essa",
        "historico": [{"papel": "edu", "texto": f"Temos {titulo}."}],
    }).json()
    assert resposta["texto"] == "Explicação detalhada"
    assert chamadas[0]["tarefa"] == "detalhar"
    assert chamadas[0]["detalhe"]["titulo"] == titulo
    assert "link" not in chamadas[0]["detalhe"]
    assert resposta["oportunidades"][0]["titulo"] == titulo


def test_titulos_da_base_chegam_a_IA(monkeypatch):
    chamadas = classificacao(monkeypatch, intencao="conversar")
    redacao(monkeypatch)
    client.post("/api/chat", json={"mensagem": "legal, me explica a fundação bradesco"})
    _, _, titulos = chamadas[0]
    assert titulos and all(isinstance(t, str) for t in titulos)


def test_perfil_faz_pergunta_sem_recomendar(monkeypatch):
    classificacao(monkeypatch, intencao="perfil")
    chamadas = redacao(monkeypatch, "Você está no ensino médio, na faculdade ou já se formou?")
    resposta = client.post("/api/chat", json={"mensagem": "estou indeciso"}).json()
    assert chamadas[0]["tarefa"] == "perguntar_perfil"
    assert resposta["oportunidades"] == [] and resposta["opcoes_online"] == []


def test_nao_sei_o_que_fazer_orienta_e_pergunta(monkeypatch):
    classificacao(monkeypatch, intencao="perfil")
    chamadas = redacao(monkeypatch, "Tudo bem! Dá para começar pensando no que você gosta de fazer.")
    resposta = client.post("/api/chat", json={"mensagem": "na verdade não sei o que fazer"}).json()
    assert chamadas[0]["tarefa"] == "perguntar_perfil"
    assert resposta["oportunidades"] == []


def test_direcionar_nao_mostra_cards_ainda(monkeypatch):
    classificacao(monkeypatch, intencao="direcionar", palavras=["saude"])
    chamadas = redacao(monkeypatch, "Que legal! Me conta sua situação atual.")
    resposta = client.post("/api/chat", json={"mensagem": "gosto da área da saúde"}).json()
    assert chamadas[0]["tarefa"] == "direcionar"
    assert chamadas[0]["itens"] == [] and chamadas[0]["online"] == []
    assert resposta["oportunidades"] == [] and resposta["opcoes_online"] == []


def test_nenhum_link_de_busca_no_google(monkeypatch):
    classificacao(monkeypatch, intencao="pedido", categoria="emprego", palavras=["xyzqwe"])
    redacao(monkeypatch)
    resposta = client.post("/api/chat", json={"mensagem": "quero ver algo raro"}).json()
    assert "google" not in resposta["texto"].lower()
    assert all("google.com" not in o["link"] for o in resposta["opcoes_online"])


def test_ia_entende_mensagem_curta_com_historico(monkeypatch):
    chamadas = classificacao(monkeypatch, intencao="pedido", categoria="cursos", palavras=["enem"])
    redacao(monkeypatch)
    client.post("/api/chat", json={
        "mensagem": "acho uma boa, pode me indicar",
        "historico": [{"papel": "usuario", "texto": "estou querendo estudar para o enem"},
                      {"papel": "edu", "texto": "Que ótima escolha!"}],
    })
    _, historico, _ = chamadas[0]
    assert historico[0]["texto"] == "estou querendo estudar para o enem"


def test_falha_na_redacao_mantem_cards(monkeypatch):
    classificacao(monkeypatch, intencao="pedido", categoria="cursos", palavras=["enem"])

    def falha(*_, **__):
        raise IAIndisponivel("teste")
    monkeypatch.setattr(main, "compor_resposta_com_ia", falha)
    resposta = client.post("/api/chat", json={"mensagem": "quero ver cursos para a prova"}).json()
    assert resposta["oportunidades"]
    assert resposta["texto"]


def test_ia_fora_do_ar_responde_sem_inventar(monkeypatch):
    def falha(*_):
        raise IAIndisponivel("teste")
    monkeypatch.setattr(main, "interpretar_com_ia", falha)
    resposta = client.post("/api/chat", json={"mensagem": "Sou estudante e gosto de programar"}).json()
    assert resposta["origem"] == "fallback"
    assert resposta["oportunidades"] == []


def test_tutorial_do_enem_usa_o_guia_e_fontes_oficiais(monkeypatch):
    classificacao(monkeypatch, intencao="tutorial", palavras=["enem", "inscricao"])
    chamadas = redacao(monkeypatch, "Passo 1: crie sua conta gov.br.")
    resposta = client.post("/api/chat", json={"mensagem": "como me inscrevo no enem?"}).json()
    assert resposta["texto"] == "Passo 1: crie sua conta gov.br."
    assert chamadas[0]["tarefa"] == "guia"
    assert resposta["opcoes_online"]
    assert all(o["link"].startswith("https://") for o in resposta["opcoes_online"])


def test_fgv_com_inscricao_pesquisa_na_web_e_nao_usa_o_guia_do_enem(monkeypatch):
    classificacao(monkeypatch, intencao="tutorial", palavras=["fgv", "inscricao"])
    redacao(monkeypatch)
    chamadas = pesquisa(monkeypatch, "A FGV funciona com provas e processos próprios.")
    resposta = client.post("/api/chat", json={"mensagem": "como me inscrevo para a fgv?"}).json()
    assert chamadas
    assert resposta["origem"] == "web"
    assert "enem" not in resposta["texto"].lower()


def test_pergunta_sobre_instituicao_fora_da_base_pesquisa(monkeypatch):
    classificacao(monkeypatch, intencao="pesquisar", palavras=["fgv", "prova"])
    chamadas = pesquisa(monkeypatch, "A FGV tem vestibular próprio.")
    resposta = client.post("/api/chat", json={"mensagem": "conhece a prova da FGV?"}).json()
    assert chamadas
    assert resposta["origem"] == "web"
    assert resposta["oportunidades"] == []


def test_pesquisa_sem_fontes_ainda_responde(monkeypatch):
    classificacao(monkeypatch, intencao="pesquisar", palavras=["fgv"])
    pesquisa(monkeypatch, "Não encontrei detalhes confiáveis.", fontes=[])
    resposta = client.post("/api/chat", json={"mensagem": "conhece a prova da FGV?"}).json()
    assert resposta["texto"] == "Não encontrei detalhes confiáveis."
    assert resposta["opcoes_online"] == []


def test_pesquisa_falha_mostra_mensagem_honesta(monkeypatch):
    classificacao(monkeypatch, intencao="pesquisar", palavras=["fgv"])

    def falha(*_):
        raise IAIndisponivel("teste")
    monkeypatch.setattr(main, "pesquisar_na_web", falha)
    resposta = client.post("/api/chat", json={"mensagem": "conhece a prova da FGV?"}).json()
    assert resposta["texto"] == rules.TEXTO_PESQUISA_FALHOU


def test_conversa_nao_traz_cards_nem_recomendacoes(monkeypatch):
    classificacao(monkeypatch, intencao="conversar")
    chamadas = redacao(monkeypatch, "Entendo. Me conta o que te atrai nessa área?")
    resposta = client.post("/api/chat", json={"mensagem": "estou pensando em mudar de carreira"}).json()
    assert chamadas[0]["tarefa"] == "conversar"
    assert resposta["oportunidades"] == [] and resposta["opcoes_online"] == []


def test_mensagem_vazia_ou_grande_e_rejeitada():
    assert client.post("/api/chat", json={"mensagem": ""}).status_code == 422
    assert client.post("/api/chat", json={"mensagem": "a" * 501}).status_code == 422


def test_limite_de_frequencia(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_POR_MINUTO", 2)
    for _ in range(2):
        assert client.post("/api/chat", json={"mensagem": "oi"}).status_code == 200
    assert client.post("/api/chat", json={"mensagem": "oi"}).status_code == 429


def test_cota_esgotada_desliga_o_chat(monkeypatch):
    classificacao(monkeypatch, intencao="pedido", categoria="cursos", palavras=["enem"])

    def esgotada(*_, **__):
        raise IAEsgotada("LIMITE_DIARIO")
    monkeypatch.setattr(main, "compor_resposta_com_ia", esgotada)
    resposta = client.post("/api/chat", json={"mensagem": "quero ver cursos para a prova"}).json()
    assert resposta["chat_indisponivel"] is True
    assert resposta["texto"] == rules.TEXTO_ESGOTADO


def test_status_reflete_a_cota(monkeypatch):
    assert client.get("/api/status").json() == {"disponivel": True}
    quota.marcar_esgotado()
    assert client.get("/api/status").json() == {"disponivel": False}


def test_limite_diario_desliga_antes_de_chamar_o_gemini(monkeypatch):
    monkeypatch.setattr(quota, "LIMITE_DIARIO_IA", 0)
    assert client.get("/api/status").json() == {"disponivel": False}
