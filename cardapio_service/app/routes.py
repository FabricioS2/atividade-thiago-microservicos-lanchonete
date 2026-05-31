from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db
from .models import Item
from .schemas import ItemCreate, ItemResponse, DisponibilidadeResponse
import uuid

router = APIRouter(prefix="/itens", tags=["itens"])

@router.get("/", response_model=list[ItemResponse])
def listar_itens(db: Session = Depends(get_db)):
    return db.query(Item).all()

@router.get("/{item_id}", response_model=ItemResponse)
def obter_item(item_id: str, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item não encontrado")
    return item

@router.post("/", response_model=ItemResponse, status_code=201)
def criar_item(item: ItemCreate, db: Session = Depends(get_db)):
    novo = Item(id=str(uuid.uuid4()), **item.model_dump())
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@router.put("/{item_id}", response_model=ItemResponse)
def atualizar_item(item_id: str, item: ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(404, "Item não encontrado")
    for key, value in item.model_dump().items():
        setattr(db_item, key, value)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/{item_id}")
def remover_item(item_id: str, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(404, "Item não encontrado")
    db.delete(db_item)
    db.commit()
    return {"ok": True}

@router.get("/{item_id}/disponibilidade", response_model=DisponibilidadeResponse)
def verificar_disponibilidade(item_id: str, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item não encontrado")
    return {"disponivel": item.disponivel, "preco": item.preco}