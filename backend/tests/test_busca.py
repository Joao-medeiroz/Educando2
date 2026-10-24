from app import opportunities


def test_base_carrega_todas_as_categorias():
    categorias = {item["categoria"] for item in opportunities.carregar_base()}
    assert categorias == {"cursos", "emprego", "idiomas", "intercambio"}


def test_itens_sem_link_sao_descartados():
    for item in opportunities.carregar_base():
        assert item["link"].startswith("https://")
        assert item["titulo"]


def test_filtra_por_categoria():
    itens = opportunities.buscar(categoria="idiomas", palavras=["ingles"], limite=10)
    assert all(i["categoria"] == "idiomas" for i in itens)


def test_palavras_comuns_nao_entram_na_busca():
    palavras = opportunities.limpar_palavras("e para enem, tem oportunidades?")
    assert "enem" in palavras
    assert "para" not in palavras and "tem" not in palavras


def test_busca_da_ia_nao_mostra_itens_sem_relacao():
    assert opportunities.buscar("emprego", ["xyzqwe"], geral_se_sem_match=False) == []


def test_busca_por_regras_mostra_a_categoria_quando_nao_ha_palavra_certa():
    itens = opportunities.buscar("emprego", ["xyzqwe"], geral_se_sem_match=True)
    assert itens and all(i["categoria"] == "emprego" for i in itens)


def test_opcoes_online_sao_oficiais_e_sem_categoria_nao_sugere():
    assert all(o["link"].startswith("https://") for o in opportunities.opcoes_online("cursos"))
    assert opportunities.opcoes_online(None) == []


def test_opcoes_online_por_assunto_saude():
    titulos = [o["titulo"] for o in opportunities.opcoes_online(None, ["saude"])]
    assert any("UNA-SUS" in t for t in titulos)


def test_opcoes_online_por_assunto_tecnologia():
    titulos = [o["titulo"] for o in opportunities.opcoes_online(None, ["tecnologia"])]
    assert any("AWS" in t or "Santander" in t for t in titulos)


def test_opcoes_online_links_sao_https():
    for categoria in ["cursos", "emprego", "idiomas"]:
        for o in opportunities.opcoes_online(categoria, ["xyzqwe"]):
            assert o["link"].startswith("https://")
