import random
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .database import get_db
from .models import Transacao, FormaPagamento
from .schemas import PagamentoRequest, PagamentoResponse

router = APIRouter(prefix="/pagamentos", tags=["pagamentos"])

@router.post("/", response_model=PagamentoResponse, status_code=201)
def processar_pagamento(pag: PagamentoRequest, db: Session = Depends(get_db)):
    # Verifica se forma de pagamento existe e está ativa
    forma = db.query(FormaPagamento).filter(FormaPagamento.id == pag.forma_pagamento_id, FormaPagamento.ativo == True).first()
    if not forma:
        raise HTTPException(400, "Forma de pagamento inválida")
    
    # Simula aprovação: 80% de chance de aprovar
    status = "APPROVED" if random.random() < 0.8 else "DECLINED"
    transacao = Transacao(
        pedido_id=pag.pedido_id,
        valor=pag.valor,
        forma_pagamento_id=pag.forma_pagamento_id,
        status=status
    )
    db.add(transacao)
    db.commit()
    db.refresh(transacao)
    return {"id_transacao": transacao.id_transacao, "pedido_id": transacao.pedido_id, "status": transacao.status}

@router.get("/{transacao_id}", response_model=PagamentoResponse)
def consultar_transacao(transacao_id: str, db: Session = Depends(get_db)):
    transacao = db.query(Transacao).filter(Transacao.id_transacao == transacao_id).first()
    if not transacao:
        raise HTTPException(404, "Transação não encontrada")
    return transacao

@router.post("/formas-pagamento/", status_code=201)
def criar_forma(nome: str, db: Session = Depends(get_db)):
    # Verificar se já existe
    existente = db.query(FormaPagamento).filter(FormaPagamento.nome == nome).first()
    if existente:
        raise HTTPException(400, "Forma de pagamento já cadastrada")
    forma = FormaPagamento(nome=nome, ativo=True)
    db.add(forma)
    db.commit()
    db.refresh(forma)
    return {"id": forma.id, "nome": forma.nome}