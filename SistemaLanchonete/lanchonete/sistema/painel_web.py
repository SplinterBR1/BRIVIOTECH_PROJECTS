"""
painel_web.py
Painel web (interface gráfica) para acompanhar pedidos e editar o estoque
em tempo real. Roda em um servidor Flask separado do webhook.

Uso:
    python painel_web.py
    Depois acesse http://localhost:5001 no navegador.
"""

from flask import Flask, jsonify, request, render_template

from database import inicializar_banco, popular_produtos_exemplo
from estoque import (
    listar_estoque_completo,
    atualizar_produto,
    criar_produto,
    remover_produto,
)
from pedidos import listar_pedidos, atualizar_status_pedido, STATUS_VALIDOS

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("dashboard.html", status_validos=STATUS_VALIDOS)


# ---------- API: Pedidos ----------

@app.route("/api/pedidos")
def api_listar_pedidos():
    status = request.args.get("status")
    return jsonify(listar_pedidos(status))


@app.route("/api/pedidos/<pedido_id>/status", methods=["PATCH"])
def api_atualizar_status_pedido(pedido_id):
    dados = request.get_json(silent=True) or {}
    novo_status = dados.get("status")

    if novo_status not in STATUS_VALIDOS:
        return jsonify({"erro": f"status inválido: {novo_status}"}), 400

    ok = atualizar_status_pedido(pedido_id, novo_status)
    if not ok:
        return jsonify({"erro": "pedido não encontrado"}), 404
    return jsonify({"ok": True})


# ---------- API: Estoque ----------

@app.route("/api/estoque")
def api_listar_estoque():
    produtos = [dict(p) for p in listar_estoque_completo()]
    return jsonify(produtos)


@app.route("/api/estoque/<int:produto_id>", methods=["PATCH"])
def api_atualizar_estoque(produto_id):
    dados = request.get_json(silent=True) or {}
    campos = {}

    if "nome" in dados:
        campos["nome"] = str(dados["nome"]).strip()
    if "preco" in dados:
        try:
            campos["preco"] = float(dados["preco"])
        except (TypeError, ValueError):
            return jsonify({"erro": "preço inválido"}), 400
    if "quantidade_estoque" in dados:
        try:
            campos["quantidade_estoque"] = int(dados["quantidade_estoque"])
        except (TypeError, ValueError):
            return jsonify({"erro": "quantidade inválida"}), 400
    if "estoque_minimo" in dados:
        try:
            campos["estoque_minimo"] = int(dados["estoque_minimo"])
        except (TypeError, ValueError):
            return jsonify({"erro": "estoque mínimo inválido"}), 400

    ok = atualizar_produto(produto_id, campos)
    if not ok:
        return jsonify({"erro": "produto não encontrado ou nenhum campo válido enviado"}), 400
    return jsonify({"ok": True})


@app.route("/api/estoque", methods=["POST"])
def api_criar_produto():
    dados = request.get_json(silent=True) or {}
    try:
        novo_id = criar_produto(
            nome=str(dados["nome"]).strip(),
            preco=float(dados["preco"]),
            quantidade_estoque=int(dados.get("quantidade_estoque", 0)),
            estoque_minimo=int(dados.get("estoque_minimo", 5)),
        )
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({"erro": f"dados inválidos: {e}"}), 400
    return jsonify({"ok": True, "id": novo_id})


@app.route("/api/estoque/<int:produto_id>", methods=["DELETE"])
def api_remover_produto(produto_id):
    ok = remover_produto(produto_id)
    if not ok:
        return jsonify({"erro": "produto não encontrado"}), 404
    return jsonify({"ok": True})


if __name__ == "__main__":
    inicializar_banco()
    popular_produtos_exemplo()
    app.run(host="0.0.0.0", port=5001, debug=True)
