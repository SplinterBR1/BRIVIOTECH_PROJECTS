# -*- coding: utf-8 -*-
"""
Ponto de entrada do sistema.

Executa o servidor do webhook do WhatsApp em uma thread separada e abre a
interface gráfica na thread principal. Para usar, rode:

    python main.py
"""

import threading

import database
import webhook
import gui


def main():
    database.iniciar_banco()

    thread_webhook = threading.Thread(target=webhook.iniciar_servidor, daemon=True)
    thread_webhook.start()

    gui.iniciar_gui()


if __name__ == "__main__":
    main()
