# -*- coding: utf-8 -*-
"""
Camada de acesso ao banco de dados SQLite.

Tabelas:
- produtos:       catálogo + estoque atual de cada item
- pedidos:        um pedido feito por um cliente via WhatsApp
- itens_pedido:   itens que compõem cada pedido
- conversas:      estado da conversa do chatbot para cada telefone
"""

import sqlite3
import threading
from datetime import datetime

from config import DATABASE_PATH

_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def iniciar_banco():
    with _lock, get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                preco REAL NOT NULL,
                estoque_atual INTEGER NOT NULL DEFAULT 0,
                estoque_minimo INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_telefone TEXT NOT NULL,
                cliente_nome TEXT,
                endereco TEXT,
                forma_pagamento TEXT,
                status TEXT NOT NULL DEFAULT 'novo',
                total REAL NOT NULL DEFAULT 0,
                criado_em TEXT NOT NULL,
                impresso INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS itens_pedido (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
                produto_id INTEGER NOT NULL REFERENCES produtos(id),
                nome_produto TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                preco_unitario REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversas (
                telefone TEXT PRIMARY KEY,
                estado TEXT NOT NULL DEFAULT 'inicio',
                dados_temp TEXT NOT NULL DEFAULT '{}',
                atualizado_em TEXT NOT NULL
            );
            """
        )
        conn.commit()

        # Popula alguns produtos de exemplo se o catálogo estiver vazio
        cur = conn.execute("SELECT COUNT(*) AS c FROM produtos")
        if cur.fetchone()["c"] == 0:
            produtos_exemplo = [
                ("X-Burger", 18.0, 30, 5),
                ("X-Salada", 20.0, 30, 5),
                ("X-Bacon", 22.0, 25, 5),
                ("Batata Frita", 12.0, 40, 10),
                ("Refrigerante Lata", 6.0, 50, 10),
                ("Suco Natural", 8.0, 20, 5),
            ]
            conn.executemany(
                "INSERT INTO produtos (nome, preco, estoque_atual, estoque_minimo) VALUES (?, ?, ?, ?)",
                produtos_exemplo,
            )
            conn.commit()


# ---------------------------------------------------------------------------
# Produtos / estoque
# ---------------------------------------------------------------------------
def listar_produtos():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM produtos ORDER BY nome").fetchall()


def buscar_produto_por_nome(nome):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM produtos WHERE lower(nome) = lower(?)", (nome,)
        ).fetchone()


def buscar_produto_por_id(produto_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()


def adicionar_produto(nome, preco, estoque_atual=0, estoque_minimo=0):
    with _lock, get_conn() as conn:
        conn.execute(
            "INSERT INTO produtos (nome, preco, estoque_atual, estoque_minimo) VALUES (?, ?, ?, ?)",
            (nome, preco, estoque_atual, estoque_minimo),
        )
        conn.commit()


def atualizar_produto(produto_id, nome, preco, estoque_atual, estoque_minimo):
    with _lock, get_conn() as conn:
        conn.execute(
            """UPDATE produtos SET nome = ?, preco = ?, estoque_atual = ?, estoque_minimo = ?
               WHERE id = ?""",
            (nome, preco, estoque_atual, estoque_minimo, produto_id),
        )
        conn.commit()


def remover_produto(produto_id):
    with _lock, get_conn() as conn:
        conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
        conn.commit()


def ajustar_estoque(produto_id, delta):
    """delta positivo repõe estoque, negativo baixa (venda)."""
    with _lock, get_conn() as conn:
        conn.execute(
            "UPDATE produtos SET estoque_atual = estoque_atual + ? WHERE id = ?",
            (delta, produto_id),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Pedidos
# ---------------------------------------------------------------------------
def criar_pedido(cliente_telefone, cliente_nome, endereco, forma_pagamento, itens):
    """
    itens: lista de dicts {produto_id, nome_produto, quantidade, preco_unitario}
    Cria o pedido, baixa o estoque de cada item e retorna o id do pedido.
    """
    total = sum(i["quantidade"] * i["preco_unitario"] for i in itens)
    with _lock, get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO pedidos
               (cliente_telefone, cliente_nome, endereco, forma_pagamento, status, total, criado_em)
               VALUES (?, ?, ?, ?, 'novo', ?, ?)""",
            (cliente_telefone, cliente_nome, endereco, forma_pagamento, total, datetime.now().isoformat()),
        )
        pedido_id = cur.lastrowid

        for item in itens:
            conn.execute(
                """INSERT INTO itens_pedido (pedido_id, produto_id, nome_produto, quantidade, preco_unitario)
                   VALUES (?, ?, ?, ?, ?)""",
                (pedido_id, item["produto_id"], item["nome_produto"], item["quantidade"], item["preco_unitario"]),
            )
            conn.execute(
                "UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE id = ?",
                (item["quantidade"], item["produto_id"]),
            )
        conn.commit()
        return pedido_id


def listar_pedidos(status=None):
    with get_conn() as conn:
        if status:
            return conn.execute(
                "SELECT * FROM pedidos WHERE status = ? ORDER BY criado_em DESC", (status,)
            ).fetchall()
        return conn.execute("SELECT * FROM pedidos ORDER BY criado_em DESC").fetchall()


def buscar_pedido(pedido_id):
    with get_conn() as conn:
        pedido = conn.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
        itens = conn.execute(
            "SELECT * FROM itens_pedido WHERE pedido_id = ?", (pedido_id,)
        ).fetchall()
        return pedido, itens


def atualizar_status_pedido(pedido_id, novo_status):
    with _lock, get_conn() as conn:
        conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
        conn.commit()


def marcar_impresso(pedido_id):
    with _lock, get_conn() as conn:
        conn.execute("UPDATE pedidos SET impresso = 1 WHERE id = ?", (pedido_id,))
        conn.commit()


# ---------------------------------------------------------------------------
# Conversas do chatbot (estado por telefone)
# ---------------------------------------------------------------------------
def obter_conversa(telefone):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM conversas WHERE telefone = ?", (telefone,)).fetchone()
        if row:
            return row
        conn.execute(
            "INSERT INTO conversas (telefone, estado, dados_temp, atualizado_em) VALUES (?, 'inicio', '{}', ?)",
            (telefone, datetime.now().isoformat()),
        )
        conn.commit()
        return conn.execute("SELECT * FROM conversas WHERE telefone = ?", (telefone,)).fetchone()


def salvar_conversa(telefone, estado, dados_temp_json):
    with _lock, get_conn() as conn:
        conn.execute(
            """INSERT INTO conversas (telefone, estado, dados_temp, atualizado_em)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(telefone) DO UPDATE SET
                   estado = excluded.estado,
                   dados_temp = excluded.dados_temp,
                   atualizado_em = excluded.atualizado_em""",
            (telefone, estado, dados_temp_json, datetime.now().isoformat()),
        )
        conn.commit()


def resetar_conversa(telefone):
    salvar_conversa(telefone, "inicio", "{}")
