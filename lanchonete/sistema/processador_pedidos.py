"""
processador_pedidos.py
Monitora a pasta 'pedidos_pendentes/', valida cada pedido, registra no banco
e dá baixa no estoque. Pedidos com problema vão para 'pedidos_erro/'.

Uso:
    python processador_pedidos.py            # fica rodando e monitorando
    python processador_pedidos.py --once      # processa o que estiver na pasta e sai
"""

import json
import sys
import time
import shutil
from pathlib import Path
from datetime import datetime

from database import conectar, inicializar_banco, popular_produtos_exemplo
from estoque import (
    verificar_disponibilidade,
    dar_baixa_estoque,
    buscar_produto_por_nome,
)
from impressora import enfileirar_comanda

BASE_DIR = Path(__file__).parent
PASTA_PENDENTES = BASE_DIR / "pedidos_pendentes"
PASTA_PROCESSADOS = BASE_DIR / "pedidos_processados"
PASTA_ERRO = BASE_DIR / "pedidos_erro"

for pasta in (PASTA_PENDENTES, PASTA_PROCESSADOS, PASTA_ERRO):
    pasta.mkdir(exist_ok=True)


def carregar_pedido(caminho_arquivo):
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        return json.load(f)


def pedido_ja_processado(pedido_id):
    """Evita processar o mesmo pedido duas vezes (idempotência)."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM pedidos WHERE id = ?", (pedido_id,))
    existe = cursor.fetchone() is not None
    conn.close()
    return existe


def registrar_pedido(pedido):
    """
    Registra o pedido no banco e dá baixa no estoque, tudo em uma transação.
    Levanta exceção se algo falhar (o chamador decide o que fazer).
    """
    conn = conectar()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO pedidos (id, cliente_nome, cliente_telefone, status, total, criado_em)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                pedido["pedido_id"],
                pedido.get("cliente", {}).get("nome"),
                pedido["cliente"]["telefone"],
                "confirmado",
                pedido["total"],
                pedido.get("timestamp", datetime.now().isoformat()),
            ),
        )

        for item in pedido["itens"]:
            produto = buscar_produto_por_nome(item["produto"], conn)
            cursor.execute(
                """INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unit)
                   VALUES (?, ?, ?, ?)""",
                (pedido["pedido_id"], produto["id"], item["quantidade"], item["preco_unit"]),
            )
            dar_baixa_estoque(
                produto["id"], item["quantidade"], motivo=f"pedido {pedido['pedido_id']}", conn=conn
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def processar_arquivo(caminho_arquivo):
    nome_arquivo = caminho_arquivo.name
    try:
        pedido = carregar_pedido(caminho_arquivo)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[ERRO] Arquivo inválido {nome_arquivo}: {e}")
        shutil.move(str(caminho_arquivo), str(PASTA_ERRO / nome_arquivo))
        return

    pedido_id = pedido.get("pedido_id", nome_arquivo)

    if pedido_ja_processado(pedido_id):
        print(f"[AVISO] Pedido {pedido_id} já processado antes, ignorando.")
        shutil.move(str(caminho_arquivo), str(PASTA_PROCESSADOS / nome_arquivo))
        return

    ok, problemas = verificar_disponibilidade(pedido["itens"])

    if not ok:
        print(f"[ESTOQUE INSUFICIENTE] Pedido {pedido_id}:")
        for p in problemas:
            print(f"   - {p}")
        pedido["status"] = "estoque_insuficiente"
        pedido["problemas"] = problemas
        with open(PASTA_ERRO / nome_arquivo, "w", encoding="utf-8") as f:
            json.dump(pedido, f, ensure_ascii=False, indent=2)
        caminho_arquivo.unlink()
        # TODO: aqui é o ponto para notificar o cliente de volta via WhatsApp
        return

    try:
        registrar_pedido(pedido)
        print(f"[OK] Pedido {pedido_id} registrado e estoque atualizado.")
        enfileirar_comanda(pedido)
        print(f"[OK] Comanda de {pedido_id} enviada para a fila de impressão.")
        shutil.move(str(caminho_arquivo), str(PASTA_PROCESSADOS / nome_arquivo))
    except Exception as e:
        print(f"[ERRO] Falha ao registrar pedido {pedido_id}: {e}")
        shutil.move(str(caminho_arquivo), str(PASTA_ERRO / nome_arquivo))


def processar_pendentes():
    arquivos = sorted(PASTA_PENDENTES.glob("*.json"))
    for arquivo in arquivos:
        processar_arquivo(arquivo)


def monitorar(intervalo_segundos=3):
    print(f"Monitorando pasta: {PASTA_PENDENTES}  (Ctrl+C para parar)")
    try:
        while True:
            processar_pendentes()
            time.sleep(intervalo_segundos)
    except KeyboardInterrupt:
        print("\nEncerrado.")


if __name__ == "__main__":
    inicializar_banco()
    popular_produtos_exemplo()

    if "--once" in sys.argv:
        processar_pendentes()
    else:
        monitorar()
