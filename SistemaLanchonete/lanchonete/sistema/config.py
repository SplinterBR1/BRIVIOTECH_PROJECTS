"""
config.py
Configurações da impressora térmica. Ajuste conforme seu equipamento.
"""

# Tipo de conexão da impressora: "rede", "usb" ou "serial"
IMPRESSORA_TIPO = "rede"

# Quando True, não tenta conectar em uma impressora de verdade — apenas
# mostra a comanda no console. Útil para testar o sistema antes de ter
# a impressora conectada. Mude para False quando for usar de verdade.
IMPRESSORA_MODO_TESTE = True

# --- Configurações para IMPRESSORA_TIPO = "rede" ---
IMPRESSORA_IP = "192.168.0.100"
IMPRESSORA_PORTA = 9100

# --- Configurações para IMPRESSORA_TIPO = "usb" ---
# Descubra os IDs com `lsusb` (Linux) e o pacote python-escpos docs.
IMPRESSORA_VENDOR_ID = 0x04b8 #É MOLODOY NESSA PORRA
IMPRESSORA_PRODUCT_ID = 0x0202

# --- Configurações para IMPRESSORA_TIPO = "serial" ---
IMPRESSORA_PORTA_SERIAL = "/dev/ttyUSB0"
IMPRESSORA_BAUDRATE = 9600

# Quantas vezes tentar reimprimir antes de mover a comanda para a fila de erro
MAX_TENTATIVAS_IMPRESSAO = 3
