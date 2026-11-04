from app import rules


def test_saudacao_sem_ia():
    assert rules.interpretar("Olá")["intencao"] == "saudacao"
    assert rules.interpretar("oi, tudo bem?")["intencao"] == "saudacao"


def test_saudacao_se_apresenta_como_edu():
    assert "Edu" in rules.TEXTO_SAUDACAO


def test_outras_mensagens_vao_para_a_ia_que_decide_a_intencao():
    # Antes as regras já mostravam oportunidades por palavra solta ("curso", "estágio").
    # Agora só a saudação é local; a IA decide se é pedido, conversa, direcionamento ou tutorial.
    for mensagem in ["quero um estágio", "curso", "cursos de idiomas", "como me inscrevo no enem?"]:
        assert rules.interpretar(mensagem)["intencao"] == "desconhecida"
