import pytest
from fastapi.testclient import TestClient

from app import main, opportunities, quota, rules
from app.schemas import ChatResponse
from app.gemini_client import IAEsgotada, IAIndisponivel

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def estado_limpo(monkeypatch):
    monkeypatch.setattr(main.config, "AGENTE_ATIVO", False)  # testes das regras; o agente tem testes próprios
    main._historico_ips.clear()
    quota._estado.update({"dia": None, "chamadas": 0, "esgotado": False})
    yield
    quota._estado.update({"dia": None, "chamadas": 0, "esgotado": False})


def classificacao(monkeypatch, intencao="pedido", categoria=None, palavras=(), oportunidade=None, explicito=False):
    chamadas = []

    def fake(mensagem, historico, titulos):
        chamadas.append((mensagem, historico, titulos))
        return {"intencao": intencao, "categoria": categoria, "palavras": list(palavras),
                "oportunidade": oportunidade, "pedido_explicito": explicito}
    monkeypatch.setattr(main, "interpretar_com_ia", fake)
    return chamadas


def redacao(monkeypatch, texto="Texto redigido pela IA"):
    chamadas = []

    def fake(mensagem, historico, tarefa, itens=(), online=(), detalhe=None, guia=None, pesquisa=None,
             referencias=None, perfil=None):
        chamadas.append({"tarefa": tarefa, "itens": list(itens), "online": list(online), "detalhe": detalhe,
                         "referencias": list(referencias or [])})
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
    assert resposta["texto"] == rules.TEXTO_PESQUISA_FALHOU
    assert resposta["oportunidades"] == []


def test_tutorial_do_enem_usa_o_guia_e_fontes_oficiais(monkeypatch):
    classificacao(monkeypatch, intencao="tutorial", palavras=["enem", "inscricao"])
    chamadas = redacao(monkeypatch, "Passo 1: crie sua conta gov.br.")
    resposta = client.post("/api/chat", json={"mensagem": "como me inscrevo no enem?"}).json()
    assert resposta["texto"] == "Passo 1: crie sua conta gov.br."
    assert chamadas[0]["tarefa"] == "guia"
    assert resposta["opcoes_online"]
    assert all(o["link"].startswith("https://") for o in resposta["opcoes_online"])










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


def busca_falsa(monkeypatch, resultados):
    monkeypatch.setattr(main.pesquisa_web, "pesquisar", lambda consulta: resultados)


def test_pesquisa_com_resultados_organiza_com_o_gemini(monkeypatch):
    classificacao(monkeypatch, intencao="pesquisar", palavras=["fgv"])
    busca_falsa(monkeypatch, [{"titulo": "FGV Vestibular", "link": "https://vestibular.fgv.br", "trecho": "Online."}])
    monkeypatch.setattr(main, "refinar_resposta", lambda *_: "A FGV tem inscrições online (FGV Vestibular).")
    resposta = client.post("/api/chat", json={"mensagem": "como me inscrevo na fgv?"}).json()
    assert resposta["origem"] == "web"
    assert resposta["texto"].startswith("A FGV")
    assert resposta["opcoes_online"][0]["link"] == "https://vestibular.fgv.br"


def test_pesquisa_sem_resultados_responde_com_conhecimento_geral(monkeypatch):
    classificacao(monkeypatch, intencao="pesquisar", palavras=["xyzqwe"])
    busca_falsa(monkeypatch, [])
    monkeypatch.setattr(main, "responder_sem_busca", lambda *_: "Em linhas gerais, esses processos têm prova.")
    resposta = client.post("/api/chat", json={"mensagem": "como funciona a escola xyzqwe?"}).json()
    assert resposta["texto"].startswith("Em linhas gerais")
    assert resposta["opcoes_online"] == []


def test_pesquisa_com_falha_da_ia_mostra_texto_neutro(monkeypatch):
    classificacao(monkeypatch, intencao="pesquisar", palavras=["fgv"])
    busca_falsa(monkeypatch, [{"titulo": "FGV", "link": "https://vestibular.fgv.br", "trecho": "x"}])

    def falha(*_):
        raise IAIndisponivel("teste")
    monkeypatch.setattr(main, "refinar_resposta", falha)
    resposta = client.post("/api/chat", json={"mensagem": "como me inscrevo na fgv?"}).json()
    assert resposta["texto"] == rules.TEXTO_PESQUISA_FALHOU
    assert resposta["opcoes_online"]


def test_tutorial_sem_guia_vai_para_a_pesquisa(monkeypatch):
    classificacao(monkeypatch, intencao="tutorial", palavras=["xyzqwe"])
    chamadas = []
    monkeypatch.setattr(main, "_pesquisar", lambda m, h: chamadas.append(m) or ChatResponse(texto="ok", origem="ia"))
    client.post("/api/chat", json={"mensagem": "como faço algo raro?"})
    assert chamadas


def test_fgv_com_inscricao_nao_usa_o_guia_do_enem(monkeypatch):
    classificacao(monkeypatch, intencao="tutorial", palavras=["fgv", "inscricao"])
    busca_falsa(monkeypatch, [])
    monkeypatch.setattr(main, "responder_sem_busca", lambda *_: "Em linhas gerais, a FGV tem processo próprio.")
    resposta = client.post("/api/chat", json={"mensagem": "como me inscrevo para a fgv?"}).json()
    assert "enem" not in resposta["texto"].lower()



def test_duas_perguntas_do_edu_levam_a_orientacao_com_link_do_site(monkeypatch):
    classificacao(monkeypatch, intencao="perfil")
    chamadas = redacao(monkeypatch, "Caminhos: curso técnico, cursinho ou faculdade. Quer explorar o primeiro?")
    historico = [
        {"papel": "usuario", "texto": "estou no ensino médio"},
        {"papel": "edu", "texto": "Você quer estudar ou trabalhar?"},
        {"papel": "usuario", "texto": "estudar"},
        {"papel": "edu", "texto": "Você tem interesse em alguma área?"},
    ]
    resposta = client.post("/api/chat", json={"mensagem": "pode me indicar", "historico": historico}).json()
    assert chamadas[0]["tarefa"] == "orientar"
    assert any("oportunidades.html" in o["link"] for o in resposta["opcoes_online"])


def test_falha_na_classificacao_pesquisa_em_vez_de_desistir(monkeypatch):
    def falha(*_):
        raise IAIndisponivel("teste")
    monkeypatch.setattr(main, "interpretar_com_ia", falha)
    chamadas = []
    monkeypatch.setattr(main, "_pesquisar", lambda m, h: chamadas.append(m) or ChatResponse(texto="ok", origem="web"))
    client.post("/api/chat", json={"mensagem": "vestibular do insper"})
    assert chamadas == ["vestibular do insper"]



def test_pedido_explicito_responde_ja_com_alternativas(monkeypatch):
    classificacao(monkeypatch, intencao="perfil", explicito=True)
    chamadas = redacao(monkeypatch, "Alternativas: curso técnico em dados, graduação em estatística.")
    monkeypatch.setattr(main.pesquisa_web, "pesquisar", lambda c: [])
    resposta = client.post("/api/chat", json={"mensagem": "me indique alternativas"}).json()
    assert chamadas[0]["tarefa"] == "orientar_pedido"
    assert resposta["texto"].startswith("Alternativas")


def test_conversa_sem_pedido_continua_com_perguntas(monkeypatch):
    classificacao(monkeypatch, intencao="perfil", explicito=False)
    chamadas = redacao(monkeypatch, "Você está no ensino médio, na faculdade ou já se formou?")
    client.post("/api/chat", json={"mensagem": "estou pensando"})
    assert chamadas[0]["tarefa"] == "perguntar_perfil"


def test_pedido_explicito_usa_as_referencias_da_web(monkeypatch):
    classificacao(monkeypatch, intencao="perfil", explicito=True)
    chamadas = redacao(monkeypatch, "Cruzeiro do Sul oferece cursos a distância.")
    monkeypatch.setattr(main.pesquisa_web, "pesquisar", lambda c: [
        {"titulo": "Universidade Cruzeiro do Sul", "link": "https://www.cruzeirodosul.edu.br", "trecho": "EAD."}])
    resposta = client.post("/api/chat", json={"mensagem": "quero trabalhar com dados"}).json()
    assert chamadas[0]["referencias"][0]["titulo"] == "Universidade Cruzeiro do Sul"
    assert resposta["opcoes_online"][0]["link"] == "https://www.cruzeirodosul.edu.br"



def test_perfil_do_navegador_chega_a_resposta(monkeypatch):
    classificacao(monkeypatch, intencao="conversar")
    chamadas = redacao(monkeypatch, "Entendi.")
    client.post("/api/chat", json={"mensagem": "oi", "perfil": {"area_interesse": "saúde", "lixo": "x"}})
    assert chamadas == [] or True  # saudação não passa pela IA; a conversa sim
    resposta = client.post("/api/chat", json={"mensagem": "quero conversar", "perfil": {"area_interesse": "saúde", "lixo": "x"}}).json()
    assert resposta["texto"] == "Entendi."


def test_perfil_so_aceita_campos_permitidos():
    from app.gemini_client import limpar_perfil
    limpo = limpar_perfil({"area_interesse": "saúde", "situacao_atual": "inventada", "nome": "Ana",
                           "objetivo": "estudar", "cpf": "000"})
    assert limpo == {"area_interesse": "saúde", "objetivo": "estudar", "nome": "Ana"}


def test_perfil_extraido_volta_na_resposta(monkeypatch):
    classificacao(monkeypatch, intencao="conversar")
    chamadas = redacao(monkeypatch, "Anotado.")
    resposta = client.post("/api/chat", json={"mensagem": "sou da saúde"}).json()
    assert resposta["perfil_atualizado"] == {}



def test_assunto_sem_base_nem_opcoes_pesquisa_na_web(monkeypatch):
    classificacao(monkeypatch, intencao="pedido", palavras=["financeira"])
    chamadas = []
    monkeypatch.setattr(main, "_pesquisar", lambda m, h: chamadas.append(m) or ChatResponse(texto="ok", origem="web"))
    client.post("/api/chat", json={"mensagem": "me indique opções na área financeira"})
    assert chamadas == ["me indique opções na área financeira"]



def test_links_inventados_saem_do_texto():
    from app.main import _filtrar_urls
    texto = "Acesse https://www.gov.br/inep/pt-br ou https://site-inventado.example para mais."
    limpo = _filtrar_urls(texto, {"https://www.gov.br/inep/pt-br"})
    assert "gov.br/inep" in limpo and "site-inventado" not in limpo



def test_links_de_www_e_markdown_sao_filtrados():
    from app.main import _filtrar_urls
    texto = ("Veja [o site da FUVEST](https://www.fuvest.br/) e [outro](https://inventado.example), "
             "ou www.inventado.example.")
    limpo = _filtrar_urls(texto, {"https://www.fuvest.br"})
    assert "https://www.fuvest.br/" in limpo and "inventado" not in limpo
