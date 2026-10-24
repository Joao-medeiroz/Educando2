from app import opportunities


def test_base_carrega_todas_as_categorias():
    categorias = {item["categoria"] for item in opportunities.carregar_base()}
    assert categorias == {"cursos", "emprego", "idiomas", "intercambio"}


def test_itens_sem_link_sao_descartados():
    for item in opportunities.carregar_base():
        assert item["link"].startswith("http")
        assert item["titulo"]


def test_filtra_por_categoria():
    itens = opportunities.buscar(categoria="idiomas", limite=10)
    assert itens and all(i["categoria"] == "idiomas" for i in itens)


def test_respeita_limite():
    assert len(opportunities.buscar(limite=2)) <= 2


def test_busca_sem_resultado_devolve_lista_vazia():
    assert opportunities.buscar(categoria="emprego", palavras=["xyzqwe"]) == []
