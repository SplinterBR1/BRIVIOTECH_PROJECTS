# -*- coding: utf-8 -*-
"""
Envia a comanda de um pedido para a impressora térmica.

Suporta 3 modos (definidos em config.IMPRESSORA_TIPO):
  - "usb":     impressora térmica conectada via USB (usa python-escpos)
  - "rede":    impressora térmica de rede (ESC/POS via socket TCP porta 9100)
  - "arquivo": modo de teste — grava a comanda formatada em .txt dentro
               da pasta comandas/, sem precisar de impressora física.
"""

import os
from datetime import datetime

import config


def _texto_comanda(pedido, itens):
    linhas = []
    linhas.append("=" * 32)
    linhas.append(config.NOME_LANCHONETE.center(32))
    linhas.append("=" * 32)
    linhas.append(f"Pedido #{pedido['id']}")
    linhas.append(f"Data: {pedido['criado_em'][:19].replace('T', ' ')}")
    linhas.append(f"Cliente: {pedido['cliente_nome'] or '-'}")
    linhas.append(f"Telefone: {pedido['cliente_telefone']}")
    if pedido["endereco"] and pedido["endereco"].lower() != "retirada":
        linhas.append(f"Endereco: {pedido['endereco']}")
    else:
        linhas.append("RETIRADA NO BALCAO")
    linhas.append(f"Pagamento: {pedido['forma_pagamento']}")
    linhas.append("-" * 32)
    for item in itens:
        subtotal = item["quantidade"] * item["preco_unitario"]
        linhas.append(f"{item['quantidade']}x {item['nome_produto']}")
        linhas.append(f"     R$ {item['preco_unitario']:.2f}  = R$ {subtotal:.2f}")
    linhas.append("-" * 32)
    linhas.append(f"TOTAL: R$ {pedido['total']:.2f}".rjust(32))
    linhas.append("=" * 32)
    linhas.append("")
    linhas.append("")
    return "\n".join(linhas)


def _imprimir_usb(texto):
    from escpos.printer import Usb

    p = Usb(config.IMPRESSORA_USB_VENDOR_ID, config.IMPRESSORA_USB_PRODUCT_ID)
    p.set(align="left")
    p.text(texto + "\n")
    p.cut()


def _imprimir_rede(texto):
    from escpos.printer import Network

    p = Network(config.IMPRESSORA_REDE_IP, port=config.IMPRESSORA_REDE_PORTA)
    p.set(align="left")
    p.text(texto + "\n")
    p.cut()


def _imprimir_arquivo(texto, pedido_id):
    os.makedirs(config.COMANDAS_DIR, exist_ok=True)
    nome_arquivo = f"comanda_{pedido_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    caminho = os.path.join(config.COMANDAS_DIR, nome_arquivo)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)
    return caminho


def imprimir_comanda(pedido, itens):
    """
    pedido: sqlite3.Row da tabela pedidos
    itens: lista de sqlite3.Row da tabela itens_pedido
    """
    texto = _texto_comanda(pedido, itens)

    if config.IMPRESSORA_TIPO == "usb":
        _imprimir_usb(texto)
    elif config.IMPRESSORA_TIPO == "rede":
        _imprimir_rede(texto)
    else:
        caminho = _imprimir_arquivo(texto, pedido["id"])
        return caminho

    return None
