# -*- coding: utf-8 -*-
"""
Servidor Flask que recebe as mensagens do WhatsApp (Cloud API da Meta),
manda cada mensagem para o chatbot, responde ao cliente e, quando um
pedido é fechado, envia a comanda para a impressora térmica.
"""

import requests
from flask import Flask, request, jsonify

import config
import chatbot
import database
import impressora

app = Flask(__name__)


def enviar_mensagem_whatsapp(telefone, texto):
    headers = {
        "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": telefone,
        "type": "text",
        "text": {"body": texto},
    }
    try:
        resp = requests.post(config.WHATSAPP_API_URL, headers=headers, json=payload, timeout=10)
        if resp.status_code >= 300:
            print(f"[WhatsApp] Erro ao enviar mensagem: {resp.status_code} {resp.text}")
    except requests.RequestException as exc:
        print(f"[WhatsApp] Falha de rede ao enviar mensagem: {exc}")


@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    """Endpoint chamado uma vez pela Meta para validar a URL do webhook."""
    modo = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if modo == "subscribe" and token == config.WHATSAPP_VERIFY_TOKEN:
        return challenge, 200
    return "Token de verificação inválido", 403


@app.route("/webhook", methods=["POST"])
def receber_mensagem():
    """Endpoint chamado pela Meta a cada nova mensagem recebida."""
    dados = request.get_json(silent=True) or {}

    try:
        entry = dados["entry"][0]
        change = entry["changes"][0]["value"]
        mensagens = change.get("messages")
        if not mensagens:
            # Pode ser um evento de status (entregue/lido), ignoramos.
            return jsonify({"status": "ignorado"}), 200

        msg = mensagens[0]
        telefone = msg["from"]
        tipo = msg.get("type")

        if tipo != "text":
            enviar_mensagem_whatsapp(
                telefone, "No momento só consigo processar mensagens de texto. 🙏"
            )
            return jsonify({"status": "ok"}), 200

        texto_cliente = msg["text"]["body"]

        respostas, pedido_id_criado = chatbot.processar_mensagem(telefone, texto_cliente)
        for resposta in respostas:
            enviar_mensagem_whatsapp(telefone, resposta)

        if pedido_id_criado:
            pedido, itens = database.buscar_pedido(pedido_id_criado)
            impressora.imprimir_comanda(pedido, itens)
            database.marcar_impresso(pedido_id_criado)

    except (KeyError, IndexError):
        # Payload não é uma mensagem reconhecida (ex.: eventos do WhatsApp que
        # não interessam ao chatbot). Retornamos 200 para a Meta não reenviar.
        pass

    return jsonify({"status": "ok"}), 200


def iniciar_servidor():
    database.iniciar_banco()
    app.run(host=config.WEBHOOK_HOST, port=config.WEBHOOK_PORT)


if __name__ == "__main__":
    iniciar_servidor()
