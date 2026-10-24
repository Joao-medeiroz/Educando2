from fastapi.testclient import TestClient

from app import main, opportunities
from app.gemini_client import IAIndisponivel

client = TestClient(main.app)


def setup_function():
    main._historico_ips.clear()


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

    def fake(mensagem, historico, tarefa, itens=(), online=(), detalhe=None):
        chamadas.append({"tarefa": tarefa, "itens": list(itens), "online": list(online), "detalhe": detalhe})
        return texto
    monkeypatch.setattr(main, "compor_resposta_com_ia", fake)
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


def test_pedido_por_regras_usa_so_a_redacao(monkeypatch):
    sem_classificacao(monkeypatch)
    chamadas = redacao(monkeypatch)
    resposta = client.post("/api/chat", json={"mensagem": "quero um estágio"}).json()
    assert resposta["origem"] == "regras"
    assert resposta["oportunidades"]
    assert len(chamadas) == 1 and chamadas[0]["tarefa"] == "recomendar"


def test_cards_trazem_tipo_local_e_link(monkeypatch):
    sem_classificacao(monkeypatch)
    redacao(monkeypatch)
    resposta = client.post("/api/chat", json={"mensagem": "quero um estágio"}).json()
    for o in resposta["oportunidades"]:
        assert o["titulo"] and o["descricao"]
        assert o["link"].startswith("https://")


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
    chamadas = classificacao(monkeypatch, intencao="pedido")
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


def test_direcionar_orienta_sem_forcar_cards(monkeypatch):
    classificacao(monkeypatch, intencao="direcionar", palavras=["saude"])
    chamadas = redacao(monkeypatch, "Que legal! Você pode explorar caminhos ligados à saúde.")
    resposta = client.post("/api/chat", json={"mensagem": "gosto bastante da área de saúde"}).json()
    assert chamadas[0]["tarefa"] == "direcionar"
    assert resposta["oportunidades"] == []


def test_resposta_separa_site_e_opcoes_online(monkeypatch):
    sem_classificacao(monkeypatch)
    redacao(monkeypatch)
    resposta = client.post("/api/chat", json={"mensagem": "quero um estágio"}).json()
    links_site = {o["link"] for o in resposta["oportunidades"]}
    assert all(o["link"] not in links_site for o in resposta["opcoes_online"])


def test_nenhum_link_de_busca_no_google(monkeypatch):
    classificacao(monkeypatch, intencao="pedido", categoria="emprego", palavras=["xyzqwe"])
    redacao(monkeypatch)
    resposta = client.post("/api/chat", json={"mensagem": "estou procurando algo raro"}).json()
    assert "google" not in resposta["texto"].lower()
    assert all("google.com" not in o["link"] for o in resposta["opcoes_online"])


def test_falha_na_redacao_mantem_cards(monkeypatch):
    classificacao(monkeypatch, intencao="pedido", categoria="cursos", palavras=["enem"])

    def falha(*_):
        raise IAIndisponivel("teste")
    monkeypatch.setattr(main, "compor_resposta_com_ia", falha)
    resposta = client.post("/api/chat", json={"mensagem": "quero me preparar para a prova"}).json()
    assert resposta["oportunidades"]
    assert resposta["texto"]


def test_ia_fora_do_ar_responde_sem_inventar(monkeypatch):
    def falha(*_):
        raise IAIndisponivel("teste")
    monkeypatch.setattr(main, "interpretar_com_ia", falha)
    resposta = client.post("/api/chat", json={"mensagem": "Sou estudante e gosto de programar"}).json()
    assert resposta["origem"] == "fallback"
    assert resposta["oportunidades"] == []


def test_mensagem_vazia_ou_grande_e_rejeitada():
    assert client.post("/api/chat", json={"mensagem": ""}).status_code == 422
    assert client.post("/api/chat", json={"mensagem": "a" * 501}).status_code == 422


def test_limite_de_frequencia(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_POR_MINUTO", 2)
    for _ in range(2):
        assert client.post("/api/chat", json={"mensagem": "oi"}).status_code == 200
    assert client.post("/api/chat", json={"mensagem": "oi"}).status_code == 429
