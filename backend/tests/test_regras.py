from app import rules


def test_saudacao_sem_ia():
    assert rules.interpretar("Olá")["intencao"] == "saudacao"
    assert rules.interpretar("oi, tudo bem?")["intencao"] == "saudacao"


def test_busca_simples_identifica_categoria():
    info = rules.interpretar("Quero ver estágios de tecnologia")
    assert info["intencao"] == "busca"
    assert info["categoria"] == "emprego"


def test_pergunta_aberta_vai_para_ia():
    info = rules.interpretar("Oi, tudo bem? Eu gostaria de saber oportunidades sobre a área de saúde")
    assert info["intencao"] == "desconhecida"


def test_acentos_nao_atrapalham():
    assert rules.interpretar("intercâmbio na Europa")["categoria"] == "intercambio"


def test_saudacao_se_apresenta_como_edu():
    assert "Edu" in rules.TEXTO_SAUDACAO
