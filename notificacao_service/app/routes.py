from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db
from .models import NotificacaoCozinha
from .schemas import NotificacaoResponse

router = APIRouter(prefix="/notificacoes", tags=["notificacoes"])

@router.get("/", response_model=list[NotificacaoResponse])
def listar_notificacoes(db: Session = Depends(get_db)):
    return db.query(NotificacaoCozinha).order_by(NotificacaoCozinha.criado_em.desc()).all()

@router.post("/{notificacao_id}/marcar-lida")
def marcar_lida(notificacao_id: str, db: Session = Depends(get_db)):
    notif = db.query(NotificacaoCozinha).filter(NotificacaoCozinha.id == notificacao_id).first()
    if not notif:
        raise HTTPException(404, "Notificação não encontrada")
    notif.lida = True
    db.commit()
    return {"mensagem": "Notificação marcada como lida"}