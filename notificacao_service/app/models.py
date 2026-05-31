import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from .database import Base
from datetime import datetime

class NotificacaoCozinha(Base):
    __tablename__ = "notificacoes"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pedido_id = Column(String, nullable=False)
    lida = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)