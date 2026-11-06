"""Controle da cota diária de chamadas ao Gemini.

O contador fica na memória de cada instância. Na Vercel, cada instância conta separadamente,
então é uma proteção aproximada. A cota real é controlada pelo Google: quando ela estoura, o
erro 429 também desliga o chat até o dia seguinte.
"""
from datetime import date

from .config import LIMITE_DIARIO_IA

_estado = {"dia": None, "chamadas": 0, "esgotado": False}


def _atualizar_dia() -> None:
    hoje = date.today()
    if _estado["dia"] != hoje:
        _estado.update({"dia": hoje, "chamadas": 0, "esgotado": False})


def registrar_chamada() -> None:
    _atualizar_dia()
    _estado["chamadas"] += 1


def marcar_esgotado() -> None:
    """Chamado quando o Google responde 429 (cota estourada)."""
    _atualizar_dia()
    _estado["esgotado"] = True


def disponivel() -> bool:
    _atualizar_dia()
    return not _estado["esgotado"] and _estado["chamadas"] < LIMITE_DIARIO_IA
