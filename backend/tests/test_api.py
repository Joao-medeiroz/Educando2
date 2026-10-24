from fastapi.testclient import TestClient

from app import main
from app.gemini_client import IAIndisponivel

client = TestClient(main.app)


def setup_function():
    main._historico_ips.clear()


def test_saude():
    assert client.get("/api/saude").json() == {"status": "ok"}


def test_saudacao_nao_chama_ia(monkeypatch):
    chamadas = []
    monkeypatch.setattr(main, "interpretar_com_ia", lambda m: chamadas.append(m))
    resposta = client.post("/api/chat", json={"mensagem": "Olá"}).json()
    assert resposta["origem"] == "regras"
    assert chamadas == []


def test_busca_por_regras_devolve_cartoes():
    resposta = client.post("/api/chat", json={"mensagem": "quero um estágio"}).json()
    assert resposta["origem"] == "regras"
    assert resposta["oportunidades"]
    assert all(o["link"].startswith("http") for o in resposta["oportunidades"])


def test_ia_indisponivel_cai_para_fallback(monkeypatch):
    def falha(_):
        raise IAIndisponivel("quota")
    monkeypatch.setattr(main, "interpretar_com_ia", falha)
    resposta = client.post("/api/chat", json={"mensagem": "Sou estudante e gosto de programar"}).json()
    assert resposta["origem"] == "fallback"
    assert resposta["oportunidades"] == []


def test_ia_interpreta_e_busca_na_base(monkeypatch):
    monkeypatch.setattr(main, "interpretar_com_ia",
                        lambda m: {"categoria": "cursos", "palavras": ["enem"]})
    resposta = client.post("/api/chat", json={"mensagem": "quero me preparar para a prova"}).json()
    assert resposta["origem"] == "ia"
    assert resposta["oportunidades"]
    assert all(o["categoria"] == "cursos" for o in resposta["oportunidades"])


def test_mensagem_vazia_ou_grande_e_rejeitada():
    assert client.post("/api/chat", json={"mensagem": ""}).status_code == 422
    assert client.post("/api/chat", json={"mensagem": "a" * 501}).status_code == 422


def test_limite_de_frequencia(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_POR_MINUTO", 2)
    for _ in range(2):
        assert client.post("/api/chat", json={"mensagem": "oi"}).status_code == 200
    assert client.post("/api/chat", json={"mensagem": "oi"}).status_code == 429


def test_erro_interno_nao_vaza_detalhes(monkeypatch):
    def explode(_):
        raise RuntimeError("segredo interno")
    monkeypatch.setattr(main, "interpretar_com_ia", lambda m: (_ for _ in ()).throw(IAIndisponivel("x")))
    resposta = client.post("/api/chat", json={"mensagem": "xyz qualquer"})
    assert "segredo" not in resposta.text
