# -*- coding: utf-8 -*-
"""
Simula uma conversa de pedido pelo terminal, sem precisar configurar o
WhatsApp de verdade. Útil para testar o chatbot e ver o pedido aparecer
na interface gráfica (aba Pedidos) e a comanda sendo gerada.

Uso:
    python simular_pedido.py
    (depois abra/atualize a GUI para ver o pedido)

Também dá pra simular manualmente, digitando cada mensagem:
    python simular_pedido.py --manual
"""

import sys

import database
import chatbot
import impressora

TELEFONE_TESTE = "5511988887777"


def _enviar(telefone, texto):
    print(f"\nCLIENTE: {texto}")
    respostas, pedido_id = chatbot.processar_mensagem(telefone, texto)
    for r in respostas:
        print(f"BOT: {r}")
    return pedido_id


def simulacao_automatica():
    database.iniciar_banco()
    pedido_id = None

    pedido_id = _enviar(TELEFONE_TESTE, "oi")
    pedido_id = _enviar(TELEFONE_TESTE, "2x X-Burger, 1x Batata Frita, 1x Refrigerante Lata")
    pedido_id = _enviar(TELEFONE_TESTE, "sim")
    pedido_id = _enviar(TELEFONE_TESTE, "Cliente Teste")
    pedido_id = _enviar(TELEFONE_TESTE, "Rua Exemplo, 123")
    pedido_id = _enviar(TELEFONE_TESTE, "pix")

    if pedido_id:
        pedido, itens = database.buscar_pedido(pedido_id)
        caminho = impressora.imprimir_comanda(pedido, itens)
        database.marcar_impresso(pedido_id)
        print(f"\n✅ Pedido #{pedido_id} criado com sucesso!")
        if caminho:
            print(f"Comanda salva em: {caminho}")
    else:
        print("\n⚠ O fluxo não terminou em um pedido. Confira as mensagens acima.")


def simulacao_manual():
    database.iniciar_banco()
    print("Digite as mensagens como se fosse o cliente (Ctrl+C para sair).")
    print("Comece digitando: oi\n")
    while True:
        try:
            texto = input("Você (cliente): ")
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrado.")
            break
        pedido_id = _enviar(TELEFONE_TESTE, texto)
        if pedido_id:
            pedido, itens = database.buscar_pedido(pedido_id)
            caminho = impressora.imprimir_comanda(pedido, itens)
            database.marcar_impresso(pedido_id)
            print(f"\n✅ Pedido #{pedido_id} criado e comanda gerada!")
            if caminho:
                print(f"Comanda salva em: {caminho}")


if __name__ == "__main__":
    if "--manual" in sys.argv:
        simulacao_manual()
    else:
        simulacao_automatica()
