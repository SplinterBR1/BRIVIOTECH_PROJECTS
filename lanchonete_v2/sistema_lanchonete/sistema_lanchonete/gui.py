# -*- coding: utf-8 -*-
"""
Interface gráfica do sistema, feita com Tkinter (vem embutido no Python).

Abas:
  - Pedidos: lista os pedidos recebidos pelo WhatsApp, permite ver os itens,
             mudar o status (Novo -> Em preparo -> Pronto -> Entregue) e
             reimprimir a comanda.
  - Estoque: lista os produtos do cardápio, permite editar preço/estoque,
             adicionar e remover produtos.
"""

import json
import random
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import database
import impressora

ATUALIZA_A_CADA_MS = 4000
STATUS_SEQUENCIA = ["novo", "em preparo", "pronto", "entregue"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema da Lanchonete")
        self.geometry("980x600")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.aba_pedidos = AbaPedidos(notebook)
        self.aba_estoque = AbaEstoque(notebook)

        notebook.add(self.aba_pedidos, text="Pedidos")
        notebook.add(self.aba_estoque, text="Estoque")

        self._agendar_atualizacoes()

    def _agendar_atualizacoes(self):
        self.aba_pedidos.atualizar()
        self.aba_estoque.atualizar()
        self.after(ATUALIZA_A_CADA_MS, self._agendar_atualizacoes)


# ---------------------------------------------------------------------------
# Aba de Pedidos
# ---------------------------------------------------------------------------
class AbaPedidos(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)

        colunas = ("id", "cliente", "telefone", "total", "status", "hora")
        self.tree = ttk.Treeview(self, columns=colunas, show="headings", height=18)
        titulos = {
            "id": "#",
            "cliente": "Cliente",
            "telefone": "Telefone",
            "total": "Total (R$)",
            "status": "Status",
            "hora": "Horário",
        }
        larguras = {"id": 40, "cliente": 160, "telefone": 130, "total": 90, "status": 110, "hora": 140}
        for col in colunas:
            self.tree.heading(col, text=titulos[col])
            self.tree.column(col, width=larguras[col], anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        painel_direita = ttk.Frame(self)
        painel_direita.pack(fill="y", side="right", padx=(10, 0))

        ttk.Label(painel_direita, text="Itens do pedido", font=("", 10, "bold")).pack(anchor="w")
        self.txt_itens = tk.Text(painel_direita, width=38, height=16, state="disabled")
        self.txt_itens.pack(pady=(4, 10))

        ttk.Button(painel_direita, text="Avançar status ▶", command=self._avancar_status).pack(
            fill="x", pady=2
        )
        ttk.Button(painel_direita, text="Marcar como Entregue", command=self._marcar_entregue).pack(
            fill="x", pady=2
        )
        ttk.Button(painel_direita, text="Reimprimir comanda 🖨", command=self._reimprimir).pack(
            fill="x", pady=2
        )
        ttk.Button(painel_direita, text="Atualizar agora", command=self.atualizar).pack(
            fill="x", pady=(4, 2)
        )
        ttk.Button(
            painel_direita, text="➕ Criar pedido de teste", command=self._criar_pedido_teste
        ).pack(fill="x", pady=(20, 2))

        self._pedido_selecionado = None

    def atualizar(self):
        selecionado_antes = self._pedido_selecionado
        for row in self.tree.get_children():
            self.tree.delete(row)

        for pedido in database.listar_pedidos():
            self.tree.insert(
                "",
                "end",
                iid=str(pedido["id"]),
                values=(
                    pedido["id"],
                    pedido["cliente_nome"] or "-",
                    pedido["cliente_telefone"],
                    f"{pedido['total']:.2f}",
                    pedido["status"],
                    pedido["criado_em"][:19].replace("T", " "),
                ),
            )

        if selecionado_antes and self.tree.exists(str(selecionado_antes)):
            self.tree.selection_set(str(selecionado_antes))

    def _on_select(self, _event=None):
        selecao = self.tree.selection()
        if not selecao:
            self._pedido_selecionado = None
            return
        pedido_id = int(selecao[0])
        self._pedido_selecionado = pedido_id
        pedido, itens = database.buscar_pedido(pedido_id)

        self.txt_itens.configure(state="normal")
        self.txt_itens.delete("1.0", "end")
        if pedido:
            linhas = [f"Endereço: {pedido['endereco'] or '-'}", f"Pagamento: {pedido['forma_pagamento'] or '-'}", ""]
            for item in itens:
                subtotal = item["quantidade"] * item["preco_unitario"]
                linhas.append(f"{item['quantidade']}x {item['nome_produto']} — R$ {subtotal:.2f}")
            linhas.append("")
            linhas.append(f"Total: R$ {pedido['total']:.2f}")
            self.txt_itens.insert("1.0", "\n".join(linhas))
        self.txt_itens.configure(state="disabled")

    def _avancar_status(self):
        if not self._pedido_selecionado:
            messagebox.showinfo("Aviso", "Selecione um pedido primeiro.")
            return
        pedido, _ = database.buscar_pedido(self._pedido_selecionado)
        try:
            idx = STATUS_SEQUENCIA.index(pedido["status"])
        except ValueError:
            idx = -1
        novo_idx = min(idx + 1, len(STATUS_SEQUENCIA) - 1)
        database.atualizar_status_pedido(self._pedido_selecionado, STATUS_SEQUENCIA[novo_idx])
        self.atualizar()

    def _marcar_entregue(self):
        if not self._pedido_selecionado:
            messagebox.showinfo("Aviso", "Selecione um pedido primeiro.")
            return
        database.atualizar_status_pedido(self._pedido_selecionado, "entregue")
        self.atualizar()

    def _reimprimir(self):
        if not self._pedido_selecionado:
            messagebox.showinfo("Aviso", "Selecione um pedido primeiro.")
            return
        pedido, itens = database.buscar_pedido(self._pedido_selecionado)
        try:
            caminho = impressora.imprimir_comanda(pedido, itens)
            database.marcar_impresso(pedido["id"])
            if caminho:
                messagebox.showinfo("Comanda gerada", f"Comanda salva em:\n{caminho}")
            else:
                messagebox.showinfo("Impressão", "Comanda enviada para a impressora.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erro ao imprimir", str(exc))

    def _criar_pedido_teste(self):
        """Cria um pedido fictício sem precisar do WhatsApp, só para testar
        o sistema (fluxo de estoque, aparecer na lista e imprimir comanda)."""
        produtos_com_estoque = [p for p in database.listar_produtos() if p["estoque_atual"] > 0]
        if not produtos_com_estoque:
            messagebox.showwarning("Sem estoque", "Nenhum produto com estoque disponível para o teste.")
            return

        qtd_itens = random.randint(1, min(3, len(produtos_com_estoque)))
        produtos_sorteados = random.sample(produtos_com_estoque, qtd_itens)

        itens = []
        for produto in produtos_sorteados:
            quantidade = random.randint(1, min(2, produto["estoque_atual"]))
            itens.append(
                {
                    "produto_id": produto["id"],
                    "nome_produto": produto["nome"],
                    "quantidade": quantidade,
                    "preco_unitario": produto["preco"],
                }
            )

        pedido_id = database.criar_pedido(
            cliente_telefone="5511900000000",
            cliente_nome="Cliente Teste",
            endereco="Rua Exemplo, 123 (pedido de teste)",
            forma_pagamento="pix",
            itens=itens,
        )

        pedido, itens_pedido = database.buscar_pedido(pedido_id)
        try:
            impressora.imprimir_comanda(pedido, itens_pedido)
            database.marcar_impresso(pedido_id)
        except Exception as exc:  # noqa: BLE001
            messagebox.showwarning("Pedido criado, mas houve erro ao imprimir", str(exc))

        self.atualizar()
        messagebox.showinfo(
            "Pedido de teste criado",
            f"Pedido #{pedido_id} criado com sucesso e enviado para a impressora "
            "(ou salvo em comandas/, se o modo 'arquivo' estiver ativo).",
        )


# ---------------------------------------------------------------------------
# Aba de Estoque
# ---------------------------------------------------------------------------
class AbaEstoque(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)

        colunas = ("id", "nome", "preco", "estoque", "minimo")
        self.tree = ttk.Treeview(self, columns=colunas, show="headings", height=18)
        titulos = {"id": "#", "nome": "Produto", "preco": "Preço (R$)", "estoque": "Estoque", "minimo": "Mínimo"}
        larguras = {"id": 40, "nome": 220, "preco": 100, "estoque": 90, "minimo": 90}
        for col in colunas:
            self.tree.heading(col, text=titulos[col])
            self.tree.column(col, width=larguras[col], anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.tag_configure("baixo", background="#ffdada")

        painel_direita = ttk.Frame(self)
        painel_direita.pack(fill="y", side="right", padx=(10, 0))

        ttk.Button(painel_direita, text="Adicionar produto", command=self._adicionar).pack(fill="x", pady=2)
        ttk.Button(painel_direita, text="Editar selecionado", command=self._editar).pack(fill="x", pady=2)
        ttk.Button(painel_direita, text="Repor estoque (+1)", command=lambda: self._ajustar(1)).pack(
            fill="x", pady=2
        )
        ttk.Button(painel_direita, text="Repor estoque (+10)", command=lambda: self._ajustar(10)).pack(
            fill="x", pady=2
        )
        ttk.Button(painel_direita, text="Remover produto", command=self._remover).pack(fill="x", pady=(20, 2))
        ttk.Button(painel_direita, text="Atualizar agora", command=self.atualizar).pack(fill="x", pady=2)

    def atualizar(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for produto in database.listar_produtos():
            tags = ("baixo",) if produto["estoque_atual"] <= produto["estoque_minimo"] else ()
            self.tree.insert(
                "",
                "end",
                iid=str(produto["id"]),
                values=(
                    produto["id"],
                    produto["nome"],
                    f"{produto['preco']:.2f}",
                    produto["estoque_atual"],
                    produto["estoque_minimo"],
                ),
                tags=tags,
            )

    def _selecionado(self):
        selecao = self.tree.selection()
        if not selecao:
            messagebox.showinfo("Aviso", "Selecione um produto primeiro.")
            return None
        return int(selecao[0])

    def _adicionar(self):
        nome = simpledialog.askstring("Novo produto", "Nome do produto:")
        if not nome:
            return
        preco = simpledialog.askfloat("Novo produto", "Preço (R$):", minvalue=0)
        if preco is None:
            return
        estoque = simpledialog.askinteger("Novo produto", "Estoque inicial:", minvalue=0) or 0
        minimo = simpledialog.askinteger("Novo produto", "Estoque mínimo (alerta):", minvalue=0) or 0
        try:
            database.adicionar_produto(nome, preco, estoque, minimo)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Erro", str(exc))
        self.atualizar()

    def _editar(self):
        produto_id = self._selecionado()
        if not produto_id:
            return
        produto = database.buscar_produto_por_id(produto_id)
        nome = simpledialog.askstring("Editar produto", "Nome:", initialvalue=produto["nome"])
        if not nome:
            return
        preco = simpledialog.askfloat("Editar produto", "Preço (R$):", initialvalue=produto["preco"], minvalue=0)
        if preco is None:
            return
        estoque = simpledialog.askinteger(
            "Editar produto", "Estoque atual:", initialvalue=produto["estoque_atual"], minvalue=0
        )
        if estoque is None:
            return
        minimo = simpledialog.askinteger(
            "Editar produto", "Estoque mínimo:", initialvalue=produto["estoque_minimo"], minvalue=0
        )
        if minimo is None:
            return
        database.atualizar_produto(produto_id, nome, preco, estoque, minimo)
        self.atualizar()

    def _ajustar(self, delta):
        produto_id = self._selecionado()
        if not produto_id:
            return
        database.ajustar_estoque(produto_id, delta)
        self.atualizar()

    def _remover(self):
        produto_id = self._selecionado()
        if not produto_id:
            return
        produto = database.buscar_produto_por_id(produto_id)
        if messagebox.askyesno("Confirmar", f"Remover '{produto['nome']}' do cardápio?"):
            database.remover_produto(produto_id)
            self.atualizar()


def iniciar_gui():
    database.iniciar_banco()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    iniciar_gui()
