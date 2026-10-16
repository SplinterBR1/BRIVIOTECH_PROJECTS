"""
impressora.py
Formata a comanda do pedido e gerencia a fila de impressão para a
impressora térmica (protocolo ESC/POS, via biblioteca python-escpos).
"""

import json
from pathlib import Path
from datetime import datetime

import config

BASE_DIR = Path(__file__).parent
FILA_PENDENTES = BASE_DIR / "fila_impressao" / "pendentes"
FILA_IMPRESSOS = BASE_DIR / "fila_impressao" / "impressos"
FILA_ERRO = BASE_DIR / "fila_impressao" / "erro"

for pasta in (FILA_PENDENTES, FILA_IMPRESSOS, FILA_ERRO):
    pasta.mkdir(parents=True, exist_ok=True)


def enfileirar_comanda(pedido):
    """
    Grava a comanda do pedido na fila de impressão (fila_impressao/pendentes/).
    Chamado assim que o pedido é registrado com sucesso.
    """
    comanda = {
        "pedido_id": pedido["pedido_id"],
        "cliente": pedido.get("cliente", {}),
        "itens": pedido["itens"],
        "total": pedido["total"],
        "timestamp": pedido.get("timestamp", datetime.now().isoformat()),
        "tentativas": 0,
    }
    caminho = FILA_PENDENTES / f"{pedido['pedido_id']}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(comanda, f, ensure_ascii=False, indent=2)
    return caminho


def formatar_comanda_texto(comanda, largura=32):
    """Monta o texto da comanda pronto para impressão (largura em colunas)."""
    linhas = []
    linhas.append("=" * largura)
    linhas.append("COMANDA - LANCHONETE".center(largura))
    linhas.append("=" * largura)
    linhas.append(f"Pedido: {comanda['pedido_id']}")

    cliente = comanda.get("cliente", {}) or {}
    linhas.append(f"Cliente: {cliente.get('nome') or '-'}")
    linhas.append(f"Telefone: {cliente.get('telefone') or '-'}")
    linhas.append("-" * largura)

    for item in comanda["itens"]:
        linhas.append(f"{item['quantidade']}x {item['produto']}")

    linhas.append("-" * largura)
    linhas.append(f"TOTAL: R$ {comanda['total']:.2f}")

    timestamp = comanda.get("timestamp") or datetime.now().isoformat()
    try:
        hora = datetime.fromisoformat(timestamp).strftime("%H:%M")
    except ValueError:
        hora = timestamp
    linhas.append(f"Hora: {hora}")
    linhas.append("=" * largura)

    return "\n".join(linhas)


def conectar_impressora():
    """Abre a conexão com a impressora física, conforme config.py."""
    from escpos.printer import Usb, Network, Serial

    if config.IMPRESSORA_TIPO == "rede":
        return Network(config.IMPRESSORA_IP, port=config.IMPRESSORA_PORTA)
    elif config.IMPRESSORA_TIPO == "usb":
        return Usb(config.IMPRESSORA_VENDOR_ID, config.IMPRESSORA_PRODUCT_ID)
    elif config.IMPRESSORA_TIPO == "serial":
        return Serial(config.IMPRESSORA_PORTA_SERIAL, baudrate=config.IMPRESSORA_BAUDRATE)
    else:
        raise ValueError(f"Tipo de impressora não suportado: {config.IMPRESSORA_TIPO}")


def imprimir_comanda(comanda):
    """
    Envia a comanda para a impressora térmica.
    Levanta exceção se a impressão falhar (o worker decide o retry).
    Em IMPRESSORA_MODO_TESTE, só exibe no console — não precisa de hardware.
    """
    texto = formatar_comanda_texto(comanda)

    if config.IMPRESSORA_MODO_TESTE:
        print("\n[MODO TESTE — simulação de impressão]")
        print(texto)
        print()
        return True

    impressora = conectar_impressora()
    try:
        impressora.set(align="center")
        impressora.text(texto + "\n\n")
        impressora.cut()
    finally:
        impressora.close()
    return True
