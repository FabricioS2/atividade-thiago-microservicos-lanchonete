import uuid
from sqlalchemy import Column, String, Float, Text, Integer, Boolean
from sqlalchemy.dialects.sqlite import BLOB
from .database import Base
import json

class Item(Base):
    __tablename__ = "itens"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nome = Column(String, nullable=False)
    preco = Column(Float, nullable=False)
    descricao = Column(Text)
    quantidade_estoque = Column(Integer, default=0)
    disponivel = Column(Boolean, default=True)