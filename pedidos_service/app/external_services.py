import os
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

CARDAPIO_URL = os.getenv("CARDAPIO_SERVICE_URL", "http://cardapio:8000")
PAGAMENTO_URL = os.getenv("PAGAMENTO_SERVICE_URL", "http://pagamento:8000")

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def obter_disponibilidade(item_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CARDAPIO_URL}/itens/{item_id}/disponibilidade")
        resp.raise_for_status()
        return resp.json()

async def obter_item(item_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CARDAPIO_URL}/itens/{item_id}")
        resp.raise_for_status()
        return resp.json()

async def processar_pagamento(pedido_id: str, valor: float, forma_pagamento_id: int) -> dict:
    async with httpx.AsyncClient() as client:
        payload = {
            "pedido_id": pedido_id,
            "valor": valor,
            "forma_pagamento_id": forma_pagamento_id
        }
        resp = await client.post(f"{PAGAMENTO_URL}/pagamentos/", json=payload)
        resp.raise_for_status()
        return resp.json()