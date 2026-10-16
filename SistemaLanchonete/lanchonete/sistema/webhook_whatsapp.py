"""
webhook_whatsapp.py
Recebe mensagens da API oficial do WhatsApp Business (Meta Cloud API),
interpreta o texto do pedido e grava um arquivo JSON em pedidos_pendentes/
para o processador_pedidos.py consumir.

Configuração necessária (variáveis de ambiente):
    VERIFY_TOKEN   -> token que você escolhe e cadastra no painel da Meta
    (o access token de envio de mensagens fica em enviar_whatsapp.py, se for usar)

Formato de mensagem esperado do cliente:
    PEDIDO
    2x X-Burger 
    1x Refrigerante Lata

Como rodar localmente para teste:
    pip install flask
    python webhook_whatsapp.py
    (depois exponha com ngrok ou similar para cadastrar a URL no painel da Meta)
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify

from database import conectar, inicializar_banco, popular_produtos_exemplo

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
PASTA_PENDENTES = BASE_DIR / "pedidos_pendentes"
PASTA_PENDENTES.mkdir(exist_ok=True)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "meu_token_secreto")

# Regex para linhas do tipo "2x X-Burger" ou "2 X-Burger"
PADRAO_ITEM = re.compile(r"^\s*(\d+)\s*[xX]?\s+(.+?)\s*$")


def buscar_preco_produto(nome_produto):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT preco FROM produtos WHERE LOWER(nome) = LOWER(?)", (nome_produto,))
    linha = cursor.fetchone()
    conn.close()
    return linha["preco"] if linha else None


def interpretar_mensagem(texto):
    """
    Converte o texto livre do pedido em uma lista de itens.
    Retorna (itens, erros)
    """
    itens = []
    erros = []

    linhas = [l for l in texto.strip().splitlines() if l.strip()]
    for linha in linhas:
        if linha.strip().upper() == "PEDIDO":
            continue
        match = PADRAO_ITEM.match(linha)
        if not match:
            erros.append(f"Linha não reconhecida: '{linha}'")
            continue

        quantidade = int(match.group(1))
        nome_produto = match.group(2).strip()
        preco = buscar_preco_produto(nome_produto)

        if preco is None:
            erros.append(f"Produto não encontrado no cardápio: '{nome_produto}'")
            continue

        itens.append({
            "produto": nome_produto,
            "quantidade": quantidade,
            "preco_unit": preco,
        })

    return itens, erros


def gerar_pedido_id():
    agora = datetime.now()
    prefixo = agora.strftime("PED-%Y%m%d")
    # conta quantos pedidos já existem hoje para sequenciar
    existentes = list(PASTA_PENDENTES.glob(f"{prefixo}-*.json")) + \
                 list((BASE_DIR / "pedidos_processados").glob(f"{prefixo}-*.json")) + \
                 list((BASE_DIR / "pedidos_erro").glob(f"{prefixo}-*.json"))
    numero = len(existentes) + 1
    return f"{prefixo}-{numero:04d}"


def salvar_arquivo_pedido(pedido):
    caminho = PASTA_PENDENTES / f"{pedido['pedido_id']}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(pedido, f, ensure_ascii=False, indent=2)
    return caminho


@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    """Endpoint de verificação exigido pela Meta ao cadastrar o webhook."""
    modo = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if modo == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Token inválido", 403


@app.route("/webhook", methods=["POST"])
def receber_mensagem():
    """Recebe o payload de mensagens da Meta Cloud API."""
    payload = request.get_json(silent=True) or {}

    try:
        entrada = payload["entry"][0]["changes"][0]["value"]
        mensagens = entrada.get("messages")
        if not mensagens:
            # pode ser um evento de status (entregue/lido), não é pedido
            return jsonify({"status": "ignorado"}), 200

        mensagem = mensagens[0]
        telefone = mensagem["from"]
        texto = mensagem.get("text", {}).get("body", "")

        contatos = entrada.get("contacts", [{}])
        nome_cliente = contatos[0].get("profile", {}).get("name") if contatos else None

    except (KeyError, IndexError) as e:
        return jsonify({"status": "erro", "detalhe": f"payload inesperado: {e}"}), 400

    itens, erros = interpretar_mensagem(texto)

    if erros or not itens:
        # TODO: aqui é o ponto para responder ao cliente pedindo para corrigir o pedido
        return jsonify({"status": "erro_interpretacao", "erros": erros}), 200

    total = round(sum(i["quantidade"] * i["preco_unit"] for i in itens), 2)

    pedido = {
        "pedido_id": gerar_pedido_id(),
        "cliente": {"nome": nome_cliente, "telefone": telefone},
        "itens": itens,
        "total": total,
        "status": "pendente",
        "timestamp": datetime.now().isoformat(),
    }

    caminho = salvar_arquivo_pedido(pedido)
    print(f"[WEBHOOK] Pedido salvo: {caminho.name}")

    return jsonify({"status": "recebido", "pedido_id": pedido["pedido_id"]}), 200


if __name__ == "__main__":
    inicializar_banco()
    popular_produtos_exemplo()
    app.run(host="0.0.0.0", port=5000, debug=True)
