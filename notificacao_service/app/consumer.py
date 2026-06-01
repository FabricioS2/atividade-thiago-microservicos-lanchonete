import os
import json
import asyncio
import aio_pika
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import NotificacaoCozinha

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")

async def consume():
    print("[Notificacao] Aguardando RabbitMQ...")
    while True:
        try:
            connection = await aio_pika.connect_robust(RABBITMQ_URL)
            print("[Notificacao] Conectado ao RabbitMQ")
            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=1)
                exchange = await channel.declare_exchange("pedidos", aio_pika.ExchangeType.TOPIC, durable=True)
                queue = await channel.declare_queue("cozinha_notificacao", durable=True)
                await queue.bind(exchange, routing_key="cozinha.notificar")
                print("[Notificacao] Aguardando mensagens...")
                
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        async with message.process():
                            body = json.loads(message.body.decode())
                            pedido_id = body["pedido_id"]
                            print(f"[Notificacao] Mensagem recebida para pedido {pedido_id}")
                            db = SessionLocal()
                            try:
                                nova = NotificacaoCozinha(pedido_id=pedido_id, lida=False)
                                db.add(nova)
                                db.commit()
                                print(f"[Notificacao] Notificação criada para pedido {pedido_id}")
                            except Exception as e:
                                print(f"[Notificacao] Erro ao salvar notificação: {e}")
                            finally:
                                db.close()
        except Exception as e:
            print(f"[Notificacao] Erro na conexão: {e}. Tentando novamente em 5s...")
            await asyncio.sleep(5)