import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from .database import Base
from datetime import datetime

class Transacao(Base):
    __tablename__ = "transacoes"
    id_transacao = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pedido_id = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    forma_pagamento_id = Column(Integer, nullable=False)
    status = Column(String, default="PENDING")  # PENDING, APPROVED, DECLINED
    criado_em = Column(DateTime, default=datetime.utcnow)

class FormaPagamento(Base):
    __tablename__ = "formas_pagamento"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, unique=True, nullable=False)
    ativo = Column(Boolean, default=True)