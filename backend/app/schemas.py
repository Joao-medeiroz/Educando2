"""Formatos de entrada e saída da API."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from .config import MAX_MENSAGEM_CHARS


class Turno(BaseModel):
    """Uma mensagem já trocada na conversa (enviada pelo front, nunca guardada no servidor)."""
    papel: Literal["usuario", "edu"]
    texto: str = Field(min_length=1, max_length=300)


class ChatRequest(BaseModel):
    mensagem: str = Field(min_length=1, max_length=MAX_MENSAGEM_CHARS)
    historico: List[Turno] = Field(default_factory=list, max_length=6)


class Oportunidade(BaseModel):
    titulo: str
    tipo: str = ""
    local: str = ""
    descricao: str
    link: str
    categoria: str


class OpcaoOnline(BaseModel):
    titulo: str
    descricao: str
    link: str


class ChatResponse(BaseModel):
    texto: str
    # Oportunidades cadastradas no próprio site
    oportunidades: List[Oportunidade] = []
    # Opções online oficiais, curadas em data/recursos_oficiais.json
    opcoes_online: List[OpcaoOnline] = []
    # "regras" = categoria por regras; "ia" = Gemini classificou; "fallback" = IA indisponível
    origem: str
    categoria: Optional[str] = None
