"""
pedidos.py
Funções de consulta e atualização de pedidos, usadas pelo painel web.
"""

from database import conectar

STATUS_VALIDOS = [
    "pendente",
    "confirmado",
    "em_preparo",
    "pronto",
    "entregue",
    "cancelado",
    "estoque_insuficiente",
]


def listar_pedidos(status=None):
    """Lista pedidos (mais recentes primeiro), com os itens de cada um."""
    conn = conectar()
    cursor = conn.cursor()

    if status:
        cursor.execute(
            "SELECT * FROM pedidos WHERE status = ? ORDER BY criado_em DESC", (status,)
        )
    else:
        cursor.execute("SELECT * FROM pedidos ORDER BY criado_em DESC")

    pedidos = [dict(row) for row in cursor.fetchall()]

    for pedido in pedidos:
        cursor.execute(
            """SELECT itens_pedido.quantidade, itens_pedido.preco_unit, produtos.nome
               FROM itens_pedido
               JOIN produtos ON produtos.id = itens_pedido.produto_id
               WHERE pedido_id = ?""",
            (pedido["id"],),
        )
        pedido["itens"] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return pedidos


def atualizar_status_pedido(pedido_id, novo_status):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
    conn.commit()
    alterado = cursor.rowcount > 0
    conn.close()
    return alterado
