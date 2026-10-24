from app import rules


def test_saudacao_sem_ia():
    assert rules.interpretar("Olá")["intencao"] == "saudacao"
    assert rules.interpretar("oi, tudo bem?")["intencao"] == "saudacao"


def test_busca_simples_identifica_categoria():
    info = rules.interpretar("Quero ver estágios de tecnologia")
    assert info["intencao"] == "busca"
    assert info["categoria"] == "emprego"


def test_mensagem_sem_termos_conhecidos_vai_para_ia():
    assert rules.interpretar("Sou estudante e gosto de programar")["intencao"] == "desconhecida"


def test_acentos_nao_atrapalham():
    assert rules.interpretar("intercâmbio na Europa")["categoria"] == "intercambio"
