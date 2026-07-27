"""
worker_impressao.py
Monitora fila_impressao/pendentes/, envia cada comanda para a impressora
térmica e trata falhas com retentativas automáticas.

Uso:
    python worker_impressao.py            # fica rodando e monitorando
    python worker_impressao.py --once      # processa a fila atual e sai
"""

import json
import sys
import time
import shutil

import config
from impressora import imprimir_comanda, FILA_PENDENTES, FILA_IMPRESSOS, FILA_ERRO


def processar_comanda(caminho_arquivo):
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        comanda = json.load(f)

    try:
        imprimir_comanda(comanda)
        print(f"[OK] Comanda impressa: {comanda['pedido_id']}")
        shutil.move(str(caminho_arquivo), str(FILA_IMPRESSOS / caminho_arquivo.name))

    except Exception as e:
        comanda["tentativas"] = comanda.get("tentativas", 0) + 1
        print(
            f"[ERRO] Falha ao imprimir {comanda['pedido_id']} "
            f"(tentativa {comanda['tentativas']}/{config.MAX_TENTATIVAS_IMPRESSAO}): {e}"
        )

        if comanda["tentativas"] >= config.MAX_TENTATIVAS_IMPRESSAO:
            with open(FILA_ERRO / caminho_arquivo.name, "w", encoding="utf-8") as f:
                json.dump(comanda, f, ensure_ascii=False, indent=2)
            caminho_arquivo.unlink()
            print(
                f"[FALHA DEFINITIVA] Comanda {comanda['pedido_id']} movida para "
                f"fila_impressao/erro/ após {comanda['tentativas']} tentativas."
            )
        else:
            # Regrava com o contador atualizado; permanece na fila para nova tentativa
            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                json.dump(comanda, f, ensure_ascii=False, indent=2)


def processar_fila():
    arquivos = sorted(FILA_PENDENTES.glob("*.json"))
    for arquivo in arquivos:
        processar_comanda(arquivo)


def reenviar_comandas_com_erro():
    """Move manualmente as comandas da fila de erro de volta para pendentes."""
    arquivos = sorted(FILA_ERRO.glob("*.json"))
    for arquivo in arquivos:
        with open(arquivo, "r", encoding="utf-8") as f:
            comanda = json.load(f)
        comanda["tentativas"] = 0
        with open(arquivo, "w", encoding="utf-8") as f:
            json.dump(comanda, f, ensure_ascii=False, indent=2)
        shutil.move(str(arquivo), str(FILA_PENDENTES / arquivo.name))
    print(f"{len(arquivos)} comanda(s) reenviada(s) para a fila.")


def monitorar(intervalo_segundos=3):
    print(f"Monitorando fila de impressão: {FILA_PENDENTES}  (Ctrl+C para parar)")
    try:
        while True:
            processar_fila()
            time.sleep(intervalo_segundos)
    except KeyboardInterrupt:
        print("\nEncerrado.")


if __name__ == "__main__":
    if "--once" in sys.argv:
        processar_fila()
    elif "--reenviar-erros" in sys.argv:
        reenviar_comandas_com_erro()
    else:
        monitorar()
