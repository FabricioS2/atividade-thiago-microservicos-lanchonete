from pydantic import BaseModel
from typing import Optional

class ItemBase(BaseModel):
    nome: str
    preco: float
    descricao: Optional[str] = ""
    quantidade_estoque: int = 0
    disponivel: bool = True

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: str
    class Config:
        from_attributes = True

class DisponibilidadeResponse(BaseModel):
    disponivel: bool
    preco: float