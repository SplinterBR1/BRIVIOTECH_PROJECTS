# -*- coding: utf-8 -*-
"""
Configurações do sistema.
Preencha os valores abaixo com as suas credenciais e ajustes de impressora.
"""

import os

# ---------------------------------------------------------------------------
# WhatsApp Business API (Cloud API oficial da Meta)
# Crie um app em https://developers.facebook.com/, ative o produto
# "WhatsApp" e gere um token permanente + o Phone Number ID.
# ---------------------------------------------------------------------------
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "COLOQUE_SEU_TOKEN_AQUI")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "COLOQUE_O_PHONE_NUMBER_ID_AQUI")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "token_de_verificacao_escolhido_por_voce")
WHATSAPP_API_VERSION = "v20.0"
WHATSAPP_API_URL = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"

# Porta em que o servidor Flask (webhook) vai escutar.
# Para a Meta conseguir chamar seu webhook, exponha essa porta na internet
# (ex.: ngrok, Cloudflare Tunnel ou um servidor com IP público + HTTPS).
WEBHOOK_HOST = "0.0.0.0"
WEBHOOK_PORT = 5000

# ---------------------------------------------------------------------------
# Banco de dados e comandas
#
# Usamos SEMPRE a mesma pasta fixa, dentro da pasta do usuário
# (ex.: C:\Users\SeuNome\SistemaLanchonete), não importa se o sistema está
# rodando via "python main.py", via "python simular_pedido.py" ou via o
# SistemaLanchonete.exe já empacotado, nem de qual pasta ele foi executado.
# Isso evita o problema de cada forma de execução criar um banco de dados
# diferente (e os pedidos "sumirem" por estarem em arquivos separados).
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.expanduser("~"), "SistemaLanchonete")
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_PATH = os.path.join(DATA_DIR, "lanchonete.db")
COMANDAS_DIR = os.path.join(DATA_DIR, "comandas")

# ---------------------------------------------------------------------------
# Impressora térmica
# Defina o tipo de conexão: "usb", "rede" ou "arquivo" (modo teste, sem
# impressora física — grava a comanda em um .txt na pasta comandas/).
#
# USB:  normalmente basta ligar a impressora e descobrir vendor_id/product_id
#       com o comando `lsusb` (Linux).
# REDE: use o IP da impressora (impressoras térmicas de rede escutam na
#       porta 9100 por padrão).
# ---------------------------------------------------------------------------
IMPRESSORA_TIPO = os.environ.get("IMPRESSORA_TIPO", "arquivo")  # "usb" | "rede" | "arquivo"

IMPRESSORA_USB_VENDOR_ID = 0x04b8   # exemplo: Epson
IMPRESSORA_USB_PRODUCT_ID = 0x0202  # exemplo: TM-T20

IMPRESSORA_REDE_IP = "192.168.0.100"
IMPRESSORA_REDE_PORTA = 9100

NOME_LANCHONETE = "Lanchonete da Praça"
