from pydantic import BaseModel
from datetime import datetime

class NotificacaoResponse(BaseModel):
    id: str
    pedido_id: str
    lida: bool
    criado_em: datetime
    class Config:
        from_attributes = True