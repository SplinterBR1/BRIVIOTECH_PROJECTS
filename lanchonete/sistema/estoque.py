"""
estoque.py
Funções de controle de estoque: consulta, baixa, reposição e alertas.
"""

from datetime import datetime
from database import conectar


class EstoqueInsuficienteError(Exception):
    """Lançada quando não há estoque suficiente para atender um pedido."""
    pass


def buscar_produto_por_nome(nome, conn=None):
    """Busca um produto pelo nome (case-insensitive)."""
    fechar = conn is None
    conn = conn or conectar()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM produtos WHERE LOWER(nome) = LOWER(?)", (nome,)
    )
    produto = cursor.fetchone()
    if fechar:
        conn.close()
    return produto


def verificar_disponibilidade(itens):
    """
    Verifica se há estoque suficiente para uma lista de itens.
    itens: lista de dicts [{"produto": str, "quantidade": int}, ...]
    Retorna: (True, []) se tudo ok, ou (False, [lista de problemas])
    """
    conn = conectar()
    problemas = []

    for item in itens:
        produto = buscar_produto_por_nome(item["produto"], conn)
        if produto is None:
            problemas.append(f"Produto não encontrado: {item['produto']}")
            continue
        if produto["quantidade_estoque"] < item["quantidade"]:
            problemas.append(
                f"Estoque insuficiente para {item['produto']}: "
                f"disponível {produto['quantidade_estoque']}, pedido {item['quantidade']}"
            )

    conn.close()
    return (len(problemas) == 0), problemas


def dar_baixa_estoque(produto_id, quantidade, motivo="venda", conn=None):
    """Reduz o estoque de um produto e registra a movimentação."""
    fechar = conn is None
    conn = conn or conectar()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE produtos SET quantidade_estoque = quantidade_estoque - ? WHERE id = ?",
        (quantidade, produto_id),
    )
    cursor.execute(
        """INSERT INTO movimentacao_estoque (produto_id, tipo, quantidade, motivo, data)
           VALUES (?, 'saida', ?, ?, ?)""",
        (produto_id, quantidade, motivo, datetime.now().isoformat()),
    )

    if fechar:
        conn.commit()
        conn.close()


def repor_estoque(nome_produto, quantidade, motivo="reposicao"):
    """Dá entrada de estoque para um produto (compra/produção)."""
    conn = conectar()
    produto = buscar_produto_por_nome(nome_produto, conn)
    if produto is None:
        conn.close()
        raise ValueError(f"Produto não encontrado: {nome_produto}")

    cursor = conn.cursor()
    cursor.execute(
        "UPDATE produtos SET quantidade_estoque = quantidade_estoque + ? WHERE id = ?",
        (quantidade, produto["id"]),
    )
    cursor.execute(
        """INSERT INTO movimentacao_estoque (produto_id, tipo, quantidade, motivo, data)
           VALUES (?, 'entrada', ?, ?, ?)""",
        (produto["id"], quantidade, motivo, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def listar_estoque_baixo():
    """Retorna produtos cujo estoque está no ou abaixo do mínimo definido."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM produtos WHERE quantidade_estoque <= estoque_minimo"
    )
    resultado = cursor.fetchall()
    conn.close()
    return resultado


def listar_estoque_completo():
    """Retorna todos os produtos e suas quantidades."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos ORDER BY nome")
    resultado = cursor.fetchall()
    conn.close()
    return resultado


def atualizar_produto(produto_id, campos):
    """
    Atualiza um ou mais campos de um produto.
    campos: dict com chaves permitidas: nome, preco, quantidade_estoque, estoque_minimo
    """
    permitidos = {"nome", "preco", "quantidade_estoque", "estoque_minimo"}
    sets, valores = [], []
    for chave, valor in campos.items():
        if chave in permitidos:
            sets.append(f"{chave} = ?")
            valores.append(valor)
    if not sets:
        return False

    valores.append(produto_id)
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE produtos SET {', '.join(sets)} WHERE id = ?", valores)
    conn.commit()
    alterado = cursor.rowcount > 0
    conn.close()
    return alterado


def criar_produto(nome, preco, quantidade_estoque=0, estoque_minimo=5):
    """Cadastra um novo produto no cardápio/estoque."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO produtos (nome, preco, quantidade_estoque, estoque_minimo) VALUES (?, ?, ?, ?)",
        (nome, preco, quantidade_estoque, estoque_minimo),
    )
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()
    return novo_id


def remover_produto(produto_id):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    conn.commit()
    removido = cursor.rowcount > 0
    conn.close()
    return removido
