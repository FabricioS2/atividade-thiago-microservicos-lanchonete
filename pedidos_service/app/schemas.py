from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ItemPedidoCreate(BaseModel):
    item_id: str
    quantidade: int

class PedidoCreate(BaseModel):
    itens: List[ItemPedidoCreate]

class ItemPedidoResponse(BaseModel):
    item_id: str
    nome_item: str
    quantidade: int
    preco_unitario: float
    subtotal: float

class PedidoResponse(BaseModel):
    id: str
    cliente_id: str
    status: str
    data_pedido: datetime
    itens: List[ItemPedidoResponse]
    total: float

class PagamentoRequest(BaseModel):
    forma_pagamento_id: int