from pydantic import BaseModel

class PagamentoRequest(BaseModel):
    pedido_id: str
    valor: float
    forma_pagamento_id: int

class PagamentoResponse(BaseModel):
    id_transacao: str
    pedido_id: str
    status: str