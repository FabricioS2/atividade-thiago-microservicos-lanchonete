import uuid
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class Pedido(Base):
    __tablename__ = "pedidos"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cliente_id = Column(String, nullable=False)   # ID do usuário do sistema externo
    status = Column(String, default="CRIADO")      # CRIADO, AGUARDANDO_PAGAMENTO, PREPARANDO, CANCELADO, CONCLUIDO
    data_pedido = Column(DateTime, default=datetime.utcnow)
    itens = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")

class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pedido_id = Column(String, ForeignKey("pedidos.id"))
    item_id = Column(String, nullable=False)         # ID do item no cardápio
    nome_item = Column(String, nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)
    pedido = relationship("Pedido", back_populates="itens")