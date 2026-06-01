# # """
# # Testes completos dos microserviços da lanchonete com 3 clientes simultâneos.
# # Certifique-se de que todos os containers estejam rodando (docker-compose up) antes de executar.
# # """

# # import requests
# # import time
# # import sys

# # BASE_CARDAPIO = "http://localhost:8001"
# # BASE_PEDIDOS  = "http://localhost:8002"
# # BASE_PAGAMENTO = "http://localhost:8003"
# # BASE_NOTIF    = "http://localhost:8004"

# # TIMEOUT = 5  # segundos
# # CLIENTES = ["cliente_1", "cliente_2", "cliente_3"]

# # def check(descricao, condition):
# #     if condition:
# #         print(f"[OK] {descricao}")
# #     else:
# #         print(f"[FALHA] {descricao}")
# #         sys.exit(1)

# # # ---------- 1. Health checks ----------
# # print("\n--- Health checks ---")
# # for nome, url in [("cardapio", BASE_CARDAPIO), ("pedidos", BASE_PEDIDOS),
# #                   ("pagamento", BASE_PAGAMENTO), ("notificacao", BASE_NOTIF)]:
# #     try:
# #         r = requests.get(f"{url}/health", timeout=TIMEOUT)
# #         check(f"{nome} health", r.status_code == 200 and r.json() == {"status": "ok"})
# #     except Exception as e:
# #         check(f"{nome} health", False)

# # # ---------- 2. Formas de pagamento (compartilhadas) ----------
# # print("\n--- Formas de pagamento ---")
# # r = requests.post(f"{BASE_PAGAMENTO}/pagamentos/formas-pagamento/?nome=PIX", timeout=TIMEOUT)
# # if r.status_code == 201:
# #     forma_id = r.json()["id"]
# #     print(f"   Forma PIX criada: {forma_id}")
# # else:
# #     forma_id = 1  # fallback
# #     print("   Forma PIX já existente, usando id=1.")
# # check("criar/obter forma PIX", forma_id is not None)

# # r = requests.post(f"{BASE_PAGAMENTO}/pagamentos/formas-pagamento/?nome=CREDITO", timeout=TIMEOUT)
# # check("criar forma CREDITO", r.status_code in (201, 400))

# # # ---------- Para cada cliente, executar o fluxo completo ----------
# # print("\n========== TESTANDO COM 3 CLIENTES ==========")

# # for cliente in CLIENTES:
# #     print(f"\n--- Cliente: {cliente} ---")
# #     headers = {"X-User-Id": cliente}
    
# #     # 3.1 Criar item próprio
# #     item_data = {
# #         "nome": f"Item {cliente}",
# #         "preco": 20.00,
# #         "descricao": f"Item de teste para {cliente}",
# #         "quantidade_estoque": 100,
# #         "disponivel": True
# #     }
# #     r = requests.post(f"{BASE_CARDAPIO}/itens/", json=item_data, timeout=TIMEOUT)
# #     check(f"{cliente} criar item", r.status_code == 201)
# #     item_id = r.json()["id"]
    
# #     # 3.2 Criar pedido
# #     pedido_data = {"itens": [{"item_id": item_id, "quantidade": 1}]}
# #     r = requests.post(f"{BASE_PEDIDOS}/pedidos/", json=pedido_data, headers=headers, timeout=TIMEOUT)
# #     check(f"{cliente} criar pedido", r.status_code == 201)
# #     pedido = r.json()
# #     pedido_id = pedido["id"]
# #     assert pedido["status"] == "CRIADO", f"Status inesperado: {pedido['status']}"
# #     print(f"   Pedido {pedido_id} criado com status {pedido['status']} e total {pedido['total']}")

# #     # 3.3 Listar pedidos
# #     r = requests.get(f"{BASE_PEDIDOS}/pedidos/", headers=headers, timeout=TIMEOUT)
# #     check(f"{cliente} listar pedidos", r.status_code == 200)
# #     pedidos_lista = r.json()
# #     assert len(pedidos_lista) == 1, f"Esperado 1 pedido, obtido {len(pedidos_lista)}"
# #     assert pedidos_lista[0]["id"] == pedido_id

# #     # 3.4 Obter pedido específico
# #     r = requests.get(f"{BASE_PEDIDOS}/pedidos/{pedido_id}", headers=headers, timeout=TIMEOUT)
# #     check(f"{cliente} obter pedido", r.status_code == 200 and r.json()["id"] == pedido_id)

# #     # 3.5 Pagamento com retry **corrigido** – confere se a mensagem é de aprovação
# #     print(f"{cliente} processando pagamento...")
# #     pag_data = {"forma_pagamento_id": forma_id}
# #     aprovado = False
# #     max_tentativas = 20
# #     for tentativa in range(1, max_tentativas + 1):
# #         r = requests.post(f"{BASE_PEDIDOS}/pedidos/{pedido_id}/pagar",
# #                           json=pag_data, headers=headers, timeout=TIMEOUT)
# #         if r.status_code == 200:
# #             resp = r.json()
# #             # Verifica se a mensagem contém "aprovado" (case insensitive)
# #             if "aprovado" in resp.get("mensagem", "").lower():
# #                 aprovado = True
# #                 print(f"   Pagamento APROVADO na tentativa {tentativa}")
# #                 break
# #             else:
# #                 print(f"   Tentativa {tentativa} recusada ({resp.get('status')}), repetindo em 1s...")
# #         else:
# #             print(f"   Tentativa {tentativa} erro HTTP {r.status_code}, repetindo em 1s...")
# #         time.sleep(1)

# #     if not aprovado:
# #         check(f"{cliente} pagamento aprovado após retry", False)
# #         sys.exit(1)

# #     # Aguarda um pouco e confere se o status realmente mudou para PREPARANDO
# #     time.sleep(0.5)
# #     r = requests.get(f"{BASE_PEDIDOS}/pedidos/{pedido_id}", headers=headers, timeout=TIMEOUT)
# #     check(f"{cliente} status mudou para PREPARANDO", r.json()["status"] == "PREPARANDO")

# #     # 3.6 Notificações
# #     print(f"{cliente} aguardando notificação...")
# #     notif_id = None
# #     for tentativa in range(10):
# #         r = requests.get(f"{BASE_NOTIF}/notificacoes/", timeout=TIMEOUT)
# #         for n in r.json():
# #             if n["pedido_id"] == pedido_id:
# #                 notif_id = n["id"]
# #                 break
# #         if notif_id:
# #             break
# #         time.sleep(2)
# #     check(f"{cliente} notificação encontrada", notif_id is not None)

# #     if notif_id:
# #         r = requests.post(f"{BASE_NOTIF}/notificacoes/{notif_id}/marcar-lida", timeout=TIMEOUT)
# #         check(f"{cliente} marcar notificação lida", r.status_code == 200)

# #     # 3.7 Tentar cancelar pedido em PREPARANDO – deve falhar
# #     r = requests.patch(f"{BASE_PEDIDOS}/pedidos/{pedido_id}/cancelar", headers=headers, timeout=TIMEOUT)
# #     check(f"{cliente} cancelar pedido em preparação deve falhar", r.status_code in (400, 422))

# #     # 3.8 Criar segundo pedido e cancelá-lo (ainda CRIADO)
# #     pedido2_data = {"itens": [{"item_id": item_id, "quantidade": 1}]}
# #     r = requests.post(f"{BASE_PEDIDOS}/pedidos/", json=pedido2_data, headers=headers, timeout=TIMEOUT)
# #     check(f"{cliente} criar segundo pedido", r.status_code == 201)
# #     pedido2_id = r.json()["id"]
# #     r = requests.patch(f"{BASE_PEDIDOS}/pedidos/{pedido2_id}/cancelar", headers=headers, timeout=TIMEOUT)
# #     check(f"{cliente} cancelar pedido CRIADO", r.status_code == 200)
# #     r = requests.get(f"{BASE_PEDIDOS}/pedidos/{pedido2_id}", headers=headers, timeout=TIMEOUT)
# #     check(f"{cliente} status do pedido cancelado", r.json()["status"] == "CANCELADO")

# #     # 3.9 Limpeza do item
# #     requests.delete(f"{BASE_CARDAPIO}/itens/{item_id}", timeout=TIMEOUT)
# #     print(f"   Item {item_id} deletado.")

# # # ---------- 4. Verificar isolamento ----------
# # print("\n--- Verificar isolamento entre clientes ---")
# # for cliente in CLIENTES:
# #     headers = {"X-User-Id": cliente}
# #     r = requests.get(f"{BASE_PEDIDOS}/pedidos/", headers=headers, timeout=TIMEOUT)
# #     pedidos = r.json()
# #     check(f"{cliente} possui 2 pedidos", len(pedidos) == 2)
# #     for p in pedidos:
# #         assert p["cliente_id"] == cliente, f"Pedido {p['id']} pertence a outro cliente"

# # print("\n✅ Todos os testes com 3 clientes concluídos com sucesso!")

# #!/usr/bin/env python3
# """
# Testes completos dos microserviços da lanchonete com 3 clientes simultâneos.
# Mostra todas as requisições e respostas.
# """

# import requests
# import time
# import sys
# import json

# BASE_CARDAPIO = "http://localhost:8001"
# BASE_PEDIDOS  = "http://localhost:8002"
# BASE_PAGAMENTO = "http://localhost:8003"
# BASE_NOTIF    = "http://localhost:8004"

# TIMEOUT = 5  # segundos
# CLIENTES = ["cliente_1", "cliente_2", "cliente_3"]

# def make_request(method, url, **kwargs):
#     """Executa uma requisição HTTP e imprime detalhes."""
#     print(f"\n🔸 {method} {url}")
#     if 'headers' in kwargs:
#         print(f"   Headers: {kwargs['headers']}")
#     if 'json' in kwargs:
#         print(f"   Body: {json.dumps(kwargs['json'], ensure_ascii=False)}")
#     if 'params' in kwargs:
#         print(f"   Params: {kwargs['params']}")
    
#     try:
#         r = requests.request(method, url, timeout=TIMEOUT, **kwargs)
#         print(f"   ↳ Status: {r.status_code}")
#         try:
#             print(f"     Body: {r.text[:200]}")  # primeiros 200 chars
#         except:
#             pass
#         return r
#     except Exception as e:
#         print(f"   ↳ Erro: {e}")
#         raise

# def check(descricao, condition):
#     if condition:
#         print(f"[OK] {descricao}")
#     else:
#         print(f"[FALHA] {descricao}")
#         sys.exit(1)

# # ---------- 1. Health checks ----------
# print("\n--- Health checks ---")
# for nome, url in [("cardapio", BASE_CARDAPIO), ("pedidos", BASE_PEDIDOS),
#                   ("pagamento", BASE_PAGAMENTO), ("notificacao", BASE_NOTIF)]:
#     try:
#         r = make_request("GET", f"{url}/health")
#         check(f"{nome} health", r.status_code == 200 and r.json() == {"status": "ok"})
#     except Exception as e:
#         check(f"{nome} health", False)

# # ---------- 2. Formas de pagamento ----------
# print("\n--- Formas de pagamento ---")
# r = make_request("POST", f"{BASE_PAGAMENTO}/pagamentos/formas-pagamento/?nome=PIX")
# if r.status_code == 201:
#     forma_id = r.json()["id"]
#     print(f"   Forma PIX criada: {forma_id}")
# else:
#     forma_id = 1
#     print("   Forma PIX já existente, usando id=1.")
# check("criar/obter forma PIX", forma_id is not None)

# r = make_request("POST", f"{BASE_PAGAMENTO}/pagamentos/formas-pagamento/?nome=CREDITO")
# check("criar forma CREDITO", r.status_code in (201, 400))

# # ---------- 3. Fluxo para cada cliente ----------
# print("\n========== TESTANDO COM 3 CLIENTES ==========")

# for cliente in CLIENTES:
#     print(f"\n--- Cliente: {cliente} ---")
#     headers = {"X-User-Id": cliente}
    
#     # 3.1 Criar item
#     item_data = {
#         "nome": f"Item {cliente}",
#         "preco": 20.00,
#         "descricao": f"Item de teste para {cliente}",
#         "quantidade_estoque": 100,
#         "disponivel": True
#     }
#     r = make_request("POST", f"{BASE_CARDAPIO}/itens/", json=item_data)
#     check(f"{cliente} criar item", r.status_code == 201)
#     item_id = r.json()["id"]
    
#     # 3.2 Criar pedido
#     pedido_data = {"itens": [{"item_id": item_id, "quantidade": 1}]}
#     r = make_request("POST", f"{BASE_PEDIDOS}/pedidos/", json=pedido_data, headers=headers)
#     check(f"{cliente} criar pedido", r.status_code == 201)
#     pedido = r.json()
#     pedido_id = pedido["id"]
#     assert pedido["status"] == "CRIADO", f"Status inesperado: {pedido['status']}"
#     print(f"   Pedido {pedido_id} criado com status {pedido['status']} e total {pedido['total']}")

#     # 3.3 Listar pedidos do cliente
#     r = make_request("GET", f"{BASE_PEDIDOS}/pedidos/", headers=headers)
#     check(f"{cliente} listar pedidos", r.status_code == 200)
#     pedidos_lista = r.json()
#     assert len(pedidos_lista) == 1, f"Esperado 1 pedido, obtido {len(pedidos_lista)}"
#     assert pedidos_lista[0]["id"] == pedido_id

#     # 3.4 Obter pedido específico
#     r = make_request("GET", f"{BASE_PEDIDOS}/pedidos/{pedido_id}", headers=headers)
#     check(f"{cliente} obter pedido", r.status_code == 200 and r.json()["id"] == pedido_id)

#     # 3.5 Pagamento com retry (exibe todas as tentativas)
#     print(f"{cliente} processando pagamento...")
#     pag_data = {"forma_pagamento_id": forma_id}
#     aprovado = False
#     max_tentativas = 20
#     for tentativa in range(1, max_tentativas + 1):
#         r = make_request("POST", f"{BASE_PEDIDOS}/pedidos/{pedido_id}/pagar",
#                          json=pag_data, headers=headers)
#         if r.status_code == 200:
#             resp = r.json()
#             if "aprovado" in resp.get("mensagem", "").lower():
#                 aprovado = True
#                 print(f"   ✅ Pagamento APROVADO na tentativa {tentativa}")
#                 break
#             else:
#                 print(f"   ⚠️ Recusado (status {resp.get('status')}), tentando novamente...")
#         else:
#             print(f"   ❌ Erro HTTP {r.status_code}, tentando novamente...")
#         time.sleep(1)

#     if not aprovado:
#         check(f"{cliente} pagamento aprovado após retry", False)
#         sys.exit(1)

#     time.sleep(0.5)
#     r = make_request("GET", f"{BASE_PEDIDOS}/pedidos/{pedido_id}", headers=headers)
#     check(f"{cliente} status mudou para PREPARANDO", r.json()["status"] == "PREPARANDO")

#     # 3.6 Notificações
#     print(f"{cliente} aguardando notificação...")
#     notif_id = None
#     for tentativa in range(10):
#         r = make_request("GET", f"{BASE_NOTIF}/notificacoes/")
#         for n in r.json():
#             if n["pedido_id"] == pedido_id:
#                 notif_id = n["id"]
#                 break
#         if notif_id:
#             print(f"   Notificação encontrada id={notif_id}")
#             break
#         time.sleep(2)
#     check(f"{cliente} notificação encontrada", notif_id is not None)

#     if notif_id:
#         r = make_request("POST", f"{BASE_NOTIF}/notificacoes/{notif_id}/marcar-lida")
#         check(f"{cliente} marcar notificação lida", r.status_code == 200)

#     # 3.7 Cancelar pedido em PREPARANDO (deve falhar)
#     r = make_request("PATCH", f"{BASE_PEDIDOS}/pedidos/{pedido_id}/cancelar", headers=headers)
#     check(f"{cliente} cancelar pedido em preparação deve falhar", r.status_code in (400, 422))

#     # 3.8 Criar segundo pedido e cancelá-lo
#     pedido2_data = {"itens": [{"item_id": item_id, "quantidade": 1}]}
#     r = make_request("POST", f"{BASE_PEDIDOS}/pedidos/", json=pedido2_data, headers=headers)
#     check(f"{cliente} criar segundo pedido", r.status_code == 201)
#     pedido2_id = r.json()["id"]
#     r = make_request("PATCH", f"{BASE_PEDIDOS}/pedidos/{pedido2_id}/cancelar", headers=headers)
#     check(f"{cliente} cancelar pedido CRIADO", r.status_code == 200)
#     r = make_request("GET", f"{BASE_PEDIDOS}/pedidos/{pedido2_id}", headers=headers)
#     check(f"{cliente} status do pedido cancelado", r.json()["status"] == "CANCELADO")

#     # 3.9 Deletar item
#     make_request("DELETE", f"{BASE_CARDAPIO}/itens/{item_id}")
#     print(f"   Item {item_id} deletado.")

# # ---------- 4. Isolamento ----------
# print("\n--- Verificar isolamento entre clientes ---")
# for cliente in CLIENTES:
#     headers = {"X-User-Id": cliente}
#     r = make_request("GET", f"{BASE_PEDIDOS}/pedidos/", headers=headers)
#     pedidos = r.json()
#     check(f"{cliente} possui 2 pedidos", len(pedidos) == 2)
#     for p in pedidos:
#         assert p["cliente_id"] == cliente, f"Pedido {p['id']} pertence a outro cliente"

# print("\n✅ Todos os testes com 3 clientes concluídos com sucesso!")


#!/usr/bin/env python3
"""
Testes completos dos microserviços da lanchonete com 3 clientes simultâneos.
Mostra todas as requisições e respostas (formatadas com quebras de linha).
"""

import requests
import time
import sys
import json

BASE_CARDAPIO = "http://localhost:8001"
BASE_PEDIDOS  = "http://localhost:8002"
BASE_PAGAMENTO = "http://localhost:8003"
BASE_NOTIF    = "http://localhost:8004"

TIMEOUT = 5  # segundos
CLIENTES = ["cliente_1", "cliente_2", "cliente_3"]

def make_request(method, url, **kwargs):
    """Executa uma requisição HTTP e imprime detalhes com quebras de linha."""
    print(f"\n🔸 {method} {url}")
    if 'headers' in kwargs:
        print(f"   Headers: {kwargs['headers']}")
    if 'json' in kwargs:
        # Exibe o corpo da requisição formatado com indentação
        print(f"   Body:")
        print(json.dumps(kwargs['json'], ensure_ascii=False, indent=2))
    if 'params' in kwargs:
        print(f"   Params: {kwargs['params']}")
    
    try:
        r = requests.request(method, url, timeout=TIMEOUT, **kwargs)
        print(f"   ↳ Status: {r.status_code}")
        # Tenta exibir a resposta como JSON formatado
        try:
            resp_json = r.json()
            print(f"     Body (JSON):")
            print(json.dumps(resp_json, ensure_ascii=False, indent=2))
        except:
            # Se não for JSON, exibe o texto bruto (máx 500 chars)
            raw_text = r.text[:500]
            print(f"     Body (texto):\n{raw_text}")
        return r
    except Exception as e:
        print(f"   ↳ Erro: {e}")
        raise

def check(descricao, condition):
    if condition:
        print(f"[OK] {descricao}")
    else:
        print(f"[FALHA] {descricao}")
        sys.exit(1)

# ---------- 1. Health checks ----------
print("\n--- Health checks ---")
for nome, url in [("cardapio", BASE_CARDAPIO), ("pedidos", BASE_PEDIDOS),
                  ("pagamento", BASE_PAGAMENTO), ("notificacao", BASE_NOTIF)]:
    try:
        r = make_request("GET", f"{url}/health")
        check(f"{nome} health", r.status_code == 200 and r.json() == {"status": "ok"})
    except Exception as e:
        check(f"{nome} health", False)

# ---------- 2. Formas de pagamento ----------
print("\n--- Formas de pagamento ---")
r = make_request("POST", f"{BASE_PAGAMENTO}/pagamentos/formas-pagamento/?nome=PIX")
if r.status_code == 201:
    forma_id = r.json()["id"]
    print(f"   Forma PIX criada: {forma_id}")
else:
    forma_id = 1
    print("   Forma PIX já existente, usando id=1.")
check("criar/obter forma PIX", forma_id is not None)

r = make_request("POST", f"{BASE_PAGAMENTO}/pagamentos/formas-pagamento/?nome=CREDITO")
check("criar forma CREDITO", r.status_code in (201, 400))

# ---------- 3. Fluxo para cada cliente ----------
print("\n========== TESTANDO COM 3 CLIENTES ==========")

for cliente in CLIENTES:
    print(f"\n--- Cliente: {cliente} ---")
    headers = {"X-User-Id": cliente}
    
    # 3.1 Criar item
    item_data = {
        "nome": f"Item {cliente}",
        "preco": 20.00,
        "descricao": f"Item de teste para {cliente}",
        "quantidade_estoque": 100,
        "disponivel": True
    }
    r = make_request("POST", f"{BASE_CARDAPIO}/itens/", json=item_data)
    check(f"{cliente} criar item", r.status_code == 201)
    item_id = r.json()["id"]
    
    # 3.2 Criar pedido
    pedido_data = {"itens": [{"item_id": item_id, "quantidade": 1}]}
    r = make_request("POST", f"{BASE_PEDIDOS}/pedidos/", json=pedido_data, headers=headers)
    check(f"{cliente} criar pedido", r.status_code == 201)
    pedido = r.json()
    pedido_id = pedido["id"]
    assert pedido["status"] == "CRIADO", f"Status inesperado: {pedido['status']}"
    print(f"   Pedido {pedido_id} criado com status {pedido['status']} e total {pedido['total']}")

    # 3.3 Listar pedidos do cliente
    r = make_request("GET", f"{BASE_PEDIDOS}/pedidos/", headers=headers)
    check(f"{cliente} listar pedidos", r.status_code == 200)
    pedidos_lista = r.json()
    assert len(pedidos_lista) == 1, f"Esperado 1 pedido, obtido {len(pedidos_lista)}"
    assert pedidos_lista[0]["id"] == pedido_id

    # 3.4 Obter pedido específico
    r = make_request("GET", f"{BASE_PEDIDOS}/pedidos/{pedido_id}", headers=headers)
    check(f"{cliente} obter pedido", r.status_code == 200 and r.json()["id"] == pedido_id)

    # 3.5 Pagamento com retry (exibe todas as tentativas)
    print(f"{cliente} processando pagamento...")
    pag_data = {"forma_pagamento_id": forma_id}
    aprovado = False
    max_tentativas = 20
    for tentativa in range(1, max_tentativas + 1):
        r = make_request("POST", f"{BASE_PEDIDOS}/pedidos/{pedido_id}/pagar",
                         json=pag_data, headers=headers)
        if r.status_code == 200:
            resp = r.json()
            if "aprovado" in resp.get("mensagem", "").lower():
                aprovado = True
                print(f"   ✅ Pagamento APROVADO na tentativa {tentativa}")
                break
            else:
                print(f"   ⚠️ Recusado (status {resp.get('status')}), tentando novamente...")
        else:
            print(f"   ❌ Erro HTTP {r.status_code}, tentando novamente...")
        time.sleep(1)

    if not aprovado:
        check(f"{cliente} pagamento aprovado após retry", False)
        sys.exit(1)

    time.sleep(0.5)
    r = make_request("GET", f"{BASE_PEDIDOS}/pedidos/{pedido_id}", headers=headers)
    check(f"{cliente} status mudou para PREPARANDO", r.json()["status"] == "PREPARANDO")

    # 3.6 Notificações
    print(f"{cliente} aguardando notificação...")
    notif_id = None
    for tentativa in range(10):
        r = make_request("GET", f"{BASE_NOTIF}/notificacoes/")
        for n in r.json():
            if n["pedido_id"] == pedido_id:
                notif_id = n["id"]
                break
        if notif_id:
            print(f"   Notificação encontrada id={notif_id}")
            break
        time.sleep(2)
    check(f"{cliente} notificação encontrada", notif_id is not None)

    if notif_id:
        r = make_request("POST", f"{BASE_NOTIF}/notificacoes/{notif_id}/marcar-lida")
        check(f"{cliente} marcar notificação lida", r.status_code == 200)

    # 3.7 Cancelar pedido em PREPARANDO (deve falhar)
    r = make_request("PATCH", f"{BASE_PEDIDOS}/pedidos/{pedido_id}/cancelar", headers=headers)
    check(f"{cliente} cancelar pedido em preparação deve falhar", r.status_code in (400, 422))

    # 3.8 Criar segundo pedido e cancelá-lo
    pedido2_data = {"itens": [{"item_id": item_id, "quantidade": 1}]}
    r = make_request("POST", f"{BASE_PEDIDOS}/pedidos/", json=pedido2_data, headers=headers)
    check(f"{cliente} criar segundo pedido", r.status_code == 201)
    pedido2_id = r.json()["id"]
    r = make_request("PATCH", f"{BASE_PEDIDOS}/pedidos/{pedido2_id}/cancelar", headers=headers)
    check(f"{cliente} cancelar pedido CRIADO", r.status_code == 200)
    r = make_request("GET", f"{BASE_PEDIDOS}/pedidos/{pedido2_id}", headers=headers)
    check(f"{cliente} status do pedido cancelado", r.json()["status"] == "CANCELADO")

    # 3.9 Deletar item
    make_request("DELETE", f"{BASE_CARDAPIO}/itens/{item_id}")
    print(f"   Item {item_id} deletado.")

# ---------- 4. Isolamento ----------
print("\n--- Verificar isolamento entre clientes ---")
for cliente in CLIENTES:
    headers = {"X-User-Id": cliente}
    r = make_request("GET", f"{BASE_PEDIDOS}/pedidos/", headers=headers)
    pedidos = r.json()
    check(f"{cliente} possui 2 pedidos", len(pedidos) == 2)
    for p in pedidos:
        assert p["cliente_id"] == cliente, f"Pedido {p['id']} pertence a outro cliente"

print("\n✅ Todos os testes com 3 clientes concluídos com sucesso!")