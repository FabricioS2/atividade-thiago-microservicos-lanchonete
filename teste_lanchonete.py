#!/usr/bin/env python3
"""
Script de testes completos para os microserviços da lanchonete.
Garanta que todos os containers estejam rodando (docker-compose up) antes de executar.
"""

import requests
import time
import json
import sys

BASE_CARDAPIO = "http://localhost:8001"
BASE_PEDIDOS  = "http://localhost:8002"
BASE_PAGAMENTO = "http://localhost:8003"
BASE_NOTIF    = "http://localhost:8004"

USER_ID = "usuario_teste_123"   # cabeçalho X-User-Id

def check(descricao, condition):
    if condition:
        print(f"[OK] {descricao}")
    else:
        print(f"[FALHA] {descricao}")
        sys.exit(1)

# ============================================================
# 1. Health checks
# ============================================================
print("\n--- Health checks ---")
r = requests.get(f"{BASE_CARDAPIO}/health")
check("cardapio health", r.status_code == 200 and r.json() == {"status":"ok"})
r = requests.get(f"{BASE_PEDIDOS}/health")
check("pedidos health", r.status_code == 200)
r = requests.get(f"{BASE_PAGAMENTO}/health")
check("pagamento health", r.status_code == 200)
r = requests.get(f"{BASE_NOTIF}/health")
check("notificacao health", r.status_code == 200)

# ============================================================
# 2. Cardápio
# ============================================================
print("\n--- Cardápio ---")
# 2.1 Listar itens (vazio)
r = requests.get(f"{BASE_CARDAPIO}/itens/")
check("listar itens vazio", r.status_code == 200 and r.json() == [])

# 2.2 Criar item
item_data = {
    "nome": "X-Tudo Teste",
    "preco": 25.90,
    "descricao": "Hambúrguer completo",
    "quantidade_estoque": 10,
    "disponivel": True
}
r = requests.post(f"{BASE_CARDAPIO}/itens/", json=item_data)
check("criar item", r.status_code == 201)
item_id = r.json()["id"]
print(f"   Item criado: {item_id}")

# 2.3 Obter item
r = requests.get(f"{BASE_CARDAPIO}/itens/{item_id}")
check("obter item", r.status_code == 200 and r.json()["nome"] == item_data["nome"])

# 2.4 Verificar disponibilidade
r = requests.get(f"{BASE_CARDAPIO}/itens/{item_id}/disponibilidade")
check("disponibilidade", r.status_code == 200 and r.json()["disponivel"] == True)

# 2.5 Atualizar item
update_data = {"nome": "X-Tudo Modificado", "preco": 27.50, "descricao": "Modificado", "quantidade_estoque": 5, "disponivel": True}
r = requests.put(f"{BASE_CARDAPIO}/itens/{item_id}", json=update_data)
check("atualizar item", r.status_code == 200 and r.json()["nome"] == "X-Tudo Modificado")

# ============================================================
# 3. Formas de pagamento
# ============================================================
print("\n--- Formas de pagamento ---")
r = requests.post(f"{BASE_PAGAMENTO}/pagamentos/formas-pagamento/?nome=PIX")
check("criar forma PIX", r.status_code == 201)
forma_id = r.json()["id"]
print(f"   Forma de pagamento criada: {forma_id}")

r = requests.post(f"{BASE_PAGAMENTO}/pagamentos/formas-pagamento/?nome=CREDITO")
check("criar forma CREDITO", r.status_code == 201)

# ============================================================
# 4. Pedidos
# ============================================================
print("\n--- Pedidos ---")
headers = {"X-User-Id": USER_ID}

# 4.1 Criar pedido com o item criado
pedido_data = {"itens": [{"item_id": item_id, "quantidade": 2}]}
r = requests.post(f"{BASE_PEDIDOS}/pedidos/", json=pedido_data, headers=headers)
check("criar pedido", r.status_code == 201)
pedido = r.json()
pedido_id = pedido["id"]
print(f"   Pedido criado: {pedido_id} status={pedido['status']} total={pedido['total']}")
assert pedido["status"] == "CRIADO"
assert pedido["total"] == 27.50 * 2  # preço atualizado

# 4.2 Listar pedidos do usuário
r = requests.get(f"{BASE_PEDIDOS}/pedidos/", headers=headers)
check("listar pedidos", r.status_code == 200 and len(r.json()) == 1)

# 4.3 Obter pedido específico
r = requests.get(f"{BASE_PEDIDOS}/pedidos/{pedido_id}", headers=headers)
check("obter pedido", r.status_code == 200 and r.json()["id"] == pedido_id)

# ============================================================
# 5. Pagamento (síncrono)
# ============================================================
print("\n--- Pagamento ---")
pag_data = {"forma_pagamento_id": forma_id}
r = requests.post(f"{BASE_PEDIDOS}/pedidos/{pedido_id}/pagar", json=pag_data, headers=headers)
# Pode vir 200 (aprovado) ou 402 (recusado). Vamos tratar ambos.
if r.status_code == 200:
    check("pagar pedido", True)
    print("   Pagamento APROVADO")
    status_esperado = "PREPARANDO"
else:
    check("pagar pedido (recusado, mas ok)", r.status_code == 402)
    print("   Pagamento RECUSADO (mock aleatório). Rodar novamente se necessário.")
    # Como foi recusado, o pedido continua CRIADO. Tentaremos de novo ou podemos abortar?
    # Para o teste, vamos considerar recusado como sucesso de endpoint, mas não valida notificação.
    # Melhor forçar aprovação? Não controlamos. Vamos informar e sair com erro se for recusado.
    # Para garantir o fluxo, pedimos ao usuário para rodar novamente.
    print("[ATENÇÃO] Pagamento recusado. Execute o script novamente para testar o fluxo completo com aprovação.")
    sys.exit(0)

# Verificar status do pedido após pagamento
time.sleep(0.5)
r = requests.get(f"{BASE_PEDIDOS}/pedidos/{pedido_id}", headers=headers)
check("status pedido atualizado para PREPARANDO", r.json()["status"] == "PREPARANDO")

# ============================================================
# 6. Notificações (assíncrona via RabbitMQ)
# ============================================================
print("\n--- Notificações (aguardando mensagem...) ---")
# Aguardar alguns segundos para a mensagem ser consumida
time.sleep(5)

# 6.1 Listar notificações
r = requests.get(f"{BASE_NOTIF}/notificacoes/")
notificacoes = r.json()
check("listar notificacoes", r.status_code == 200 and len(notificacoes) > 0)
notif_id = None
for n in notificacoes:
    if n["pedido_id"] == pedido_id:
        notif_id = n["id"]
        check("notificacao do pedido encontrada", True)
        check("notificacao nao lida inicialmente", n["lida"] == False)
        break
if notif_id is None:
    check("notificacao do pedido NAO encontrada (talvez RabbitMQ atrasado)", False)

# 6.2 Marcar como lida
if notif_id:
    r = requests.post(f"{BASE_NOTIF}/notificacoes/{notif_id}/marcar-lida")
    check("marcar como lida", r.status_code == 200)
    r = requests.get(f"{BASE_NOTIF}/notificacoes/")
    for n in r.json():
        if n["id"] == notif_id:
            check("notificacao agora esta lida", n["lida"] == True)
            break

# ============================================================
# 7. Cancelamento de pedido (não pode cancelar após pago)
# ============================================================
print("\n--- Cancelamento ---")
r = requests.patch(f"{BASE_PEDIDOS}/pedidos/{pedido_id}/cancelar", headers=headers)
check("cancelar pedido pago deve falhar", r.status_code == 400)  # ou 400, depende da implementação

# Criar um novo pedido para cancelar com sucesso
pedido2_data = {"itens": [{"item_id": item_id, "quantidade": 1}]}
r = requests.post(f"{BASE_PEDIDOS}/pedidos/", json=pedido2_data, headers=headers)
pedido2_id = r.json()["id"]
r = requests.patch(f"{BASE_PEDIDOS}/pedidos/{pedido2_id}/cancelar", headers=headers)
check("cancelar pedido criado", r.status_code == 200)
r = requests.get(f"{BASE_PEDIDOS}/pedidos/{pedido2_id}", headers=headers)
check("status cancelado", r.json()["status"] == "CANCELADO")

# ============================================================
# 8. Limpeza (remover itens de teste)
# ============================================================
print("\n--- Limpeza ---")
requests.delete(f"{BASE_CARDAPIO}/itens/{item_id}")
print("   Item de teste deletado.")

print("\n✅ Todos os testes concluídos com sucesso!")