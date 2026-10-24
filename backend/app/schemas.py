"""Formatos de entrada e saída da API (validados pelo Pydantic)."""
from typing import List, Optional
from pydantic import BaseModel, Field

from .config import MAX_MENSAGEM_CHARS


class ChatRequest(BaseModel):
    mensagem: str = Field(min_length=1, max_length=MAX_MENSAGEM_CHARS)


class Oportunidade(BaseModel):
    categoria: str
    tipo: str
    titulo: str
    descricao: str
    local: str
    link: str
    imagem: str


class ChatResponse(BaseModel):
    texto: str
    oportunidades: List[Oportunidade] = []
    # "regras" = resolvido sem IA; "ia" = Gemini interpretou; "fallback" = IA indisponível
    origem: str
    categoria: Optional[str] = None
