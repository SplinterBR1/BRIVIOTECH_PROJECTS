"""
database.py
Responsável por criar e conectar ao banco SQLite da lanchonete.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "lanchonete.db"


def conectar():
    """Retorna uma conexão com o banco, com suporte a chaves estrangeiras."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_banco():
    """Cria as tabelas do banco caso ainda não existam."""
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            preco REAL NOT NULL,
            quantidade_estoque INTEGER NOT NULL DEFAULT 0,
            estoque_minimo INTEGER NOT NULL DEFAULT 5
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id TEXT PRIMARY KEY,
            cliente_nome TEXT,
            cliente_telefone TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendente',
            total REAL NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL,
            observacao TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id TEXT NOT NULL REFERENCES pedidos(id),
            produto_id INTEGER NOT NULL REFERENCES produtos(id),
            quantidade INTEGER NOT NULL,
            preco_unit REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimentacao_estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL REFERENCES produtos(id),
            tipo TEXT NOT NULL,          -- 'entrada' ou 'saida'
            quantidade INTEGER NOT NULL,
            motivo TEXT,
            data TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def popular_produtos_exemplo():
    """Insere alguns produtos de exemplo, se o cardápio ainda estiver vazio."""
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM produtos")
    if cursor.fetchone()["total"] == 0:
        produtos_exemplo = [
            ("X-Burger", 18.00, 50, 10),
            ("X-Bacon", 22.00, 40, 10),
            ("Refrigerante Lata", 6.00, 100, 20),
            ("Suco Natural", 8.00, 30, 10),
            ("Batata Frita", 12.00, 40, 10),
        ]
        cursor.executemany(
            "INSERT INTO produtos (nome, preco, quantidade_estoque, estoque_minimo) VALUES (?, ?, ?, ?)",
            produtos_exemplo,
        )
        conn.commit()
    conn.close()


if __name__ == "__main__":
    inicializar_banco()
    popular_produtos_exemplo()
    print(f"Banco inicializado em: {DB_PATH}")
