import json
import os
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .database import get_db
from .models import Pedido, ItemPedido
from .schemas import PedidoCreate, PedidoResponse, ItemPedidoResponse, PagamentoRequest
from .external_services import obter_disponibilidade, obter_item, processar_pagamento
import aio_pika
import httpx

router = APIRouter(prefix="/pedidos", tags=["pedidos"])
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")

@router.post("/", response_model=PedidoResponse, status_code=201)
async def criar_pedido(pedido: PedidoCreate, x_user_id: str = Header(None), db: Session = Depends(get_db)):
    if not x_user_id:
        raise HTTPException(400, "Header X-User-Id obrigatório")
    
    novo_pedido = Pedido(cliente_id=x_user_id, status="CRIADO")
    db.add(novo_pedido)
    db.flush()
    
    for item_req in pedido.itens:
        disp = await obter_disponibilidade(item_req.item_id)
        if not disp["disponivel"]:
            raise HTTPException(400, f"Item {item_req.item_id} indisponível")
        
        item_info = await obter_item(item_req.item_id)
        
        item_pedido = ItemPedido(
            pedido_id=novo_pedido.id,
            item_id=item_req.item_id,
            nome_item=item_info["nome"],
            quantidade=item_req.quantidade,
            preco_unitario=item_info["preco"]
        )
        db.add(item_pedido)
    
    db.commit()
    db.refresh(novo_pedido)
    
    total = sum(i.quantidade * i.preco_unitario for i in novo_pedido.itens)
    itens_resp = [
        ItemPedidoResponse(
            item_id=i.item_id,
            nome_item=i.nome_item,
            quantidade=i.quantidade,
            preco_unitario=i.preco_unitario,
            subtotal=i.quantidade * i.preco_unitario
        ) for i in novo_pedido.itens
    ]
    return PedidoResponse(
        id=novo_pedido.id,
        cliente_id=novo_pedido.cliente_id,
        status=novo_pedido.status,
        data_pedido=novo_pedido.data_pedido,
        itens=itens_resp,
        total=total
    )

@router.get("/", response_model=list[PedidoResponse])
def listar_pedidos(x_user_id: str = Header(None), db: Session = Depends(get_db)):
    if not x_user_id:
        raise HTTPException(400, "Header X-User-Id obrigatório")
    pedidos = db.query(Pedido).filter(Pedido.cliente_id == x_user_id).all()
    result = []
    for p in pedidos:
        total = sum(i.quantidade * i.preco_unitario for i in p.itens)
        itens_resp = [ItemPedidoResponse(
            item_id=i.item_id, nome_item=i.nome_item, quantidade=i.quantidade,
            preco_unitario=i.preco_unitario, subtotal=i.quantidade * i.preco_unitario
        ) for i in p.itens]
        result.append(PedidoResponse(
            id=p.id, cliente_id=p.cliente_id, status=p.status,
            data_pedido=p.data_pedido, itens=itens_resp, total=total
        ))
    return result

@router.get("/{pedido_id}", response_model=PedidoResponse)
def obter_pedido(pedido_id: str, x_user_id: str = Header(None), db: Session = Depends(get_db)):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id, Pedido.cliente_id == x_user_id).first()
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")
    total = sum(i.quantidade * i.preco_unitario for i in pedido.itens)
    itens_resp = [ItemPedidoResponse(
        item_id=i.item_id, nome_item=i.nome_item, quantidade=i.quantidade,
        preco_unitario=i.preco_unitario, subtotal=i.quantidade * i.preco_unitario
    ) for i in pedido.itens]
    return PedidoResponse(
        id=pedido.id, cliente_id=pedido.cliente_id, status=pedido.status,
        data_pedido=pedido.data_pedido, itens=itens_resp, total=total
    )

@router.post("/{pedido_id}/pagar")
async def pagar_pedido(pedido_id: str, pag_req: PagamentoRequest, x_user_id: str = Header(None), db: Session = Depends(get_db)):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id, Pedido.cliente_id == x_user_id).first()
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")
    if pedido.status != "CRIADO":
        raise HTTPException(400, "Pedido não está elegível para pagamento")
    
    total = sum(i.quantidade * i.preco_unitario for i in pedido.itens)
    try:
        resultado = await processar_pagamento(pedido.id, total, pag_req.forma_pagamento_id)
    except Exception as e:
        raise HTTPException(502, f"Falha na comunicação com serviço de pagamento: {e}")
    
    if resultado["status"] == "APPROVED":
        pedido.status = "PREPARANDO"
        db.commit()
        # Publica mensagem persistente no RabbitMQ
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            async with connection:
                channel = await connection.channel()
                exchange = await channel.declare_exchange("pedidos", aio_pika.ExchangeType.TOPIC, durable=True)
                queue = await channel.declare_queue("cozinha_notificacao", durable=True)
                await queue.bind(exchange, routing_key="cozinha.notificar")
                
                message = aio_pika.Message(
                    body=json.dumps({"pedido_id": pedido.id}).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                )
                await exchange.publish(message, routing_key="cozinha.notificar")
                print(f"[Pedidos] Mensagem publicada para pedido {pedido.id}")
        except Exception as e:
            print(f"[Pedidos] Erro ao publicar mensagem: {e}")
        return {"mensagem": "Pagamento aprovado, pedido em preparação"}
    else:
        return {"mensagem": "Pagamento recusado", "status": resultado["status"]}

@router.patch("/{pedido_id}/cancelar")
def cancelar_pedido(pedido_id: str, x_user_id: str = Header(None), db: Session = Depends(get_db)):
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id, Pedido.cliente_id == x_user_id).first()
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")
    if pedido.status not in ("CRIADO", "AGUARDANDO_PAGAMENTO"):
        raise HTTPException(400, "Pedido não pode ser cancelado no status atual")
    pedido.status = "CANCELADO"
    db.commit()
    return {"mensagem": "Pedido cancelado"}