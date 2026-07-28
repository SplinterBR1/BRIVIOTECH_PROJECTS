# -*- coding: utf-8 -*-
"""
Chatbot simples baseado em máquina de estados.

Fluxo:
  inicio -> aguardando_itens -> aguardando_confirmacao ->
  aguardando_nome -> aguardando_endereco -> aguardando_pagamento -> finalizado

Cada função recebe o texto da mensagem do cliente e o estado atual salvo no
banco, e devolve (texto_de_resposta, novo_estado, dados_temp_atualizado).
Quando o pedido é fechado, o chatbot chama database.criar_pedido(...) e
manda a comanda para a fila de impressão (feito em webhook.py).
"""

import json
import re

import database


def montar_menu():
    produtos = database.listar_produtos()
    linhas = ["🍔 *Cardápio* 🍔"]
    for p in produtos:
        linhas.append(f"- {p['nome']}: R$ {p['preco']:.2f}")
    linhas.append("")
    linhas.append(
        "Digite seu pedido no formato:\n"
        "_2x X-Burger, 1x Batata Frita, 1x Refrigerante Lata_"
    )
    return "\n".join(linhas)


def _parse_itens(texto):
    """
    Extrai itens de uma mensagem tipo:
    "2x X-Burger, 1 Batata Frita e 1x Coca"
    Retorna lista de (quantidade, nome_produto_digitado) ou [] se nada reconhecido.
    """
    texto = texto.replace(" e ", ",")
    partes = re.split(r"[,\n]", texto)
    itens = []
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        m = re.match(r"(\d+)\s*x?\s*(.+)", parte, re.IGNORECASE)
        if m:
            qtd = int(m.group(1))
            nome = m.group(2).strip()
        else:
            qtd = 1
            nome = parte
        itens.append((qtd, nome))
    return itens


def _resolver_itens(itens_digitados):
    """
    Casa os nomes digitados pelo cliente com produtos do catálogo
    (comparação simples por substring, sem diferenciar maiúsculas).
    Retorna (itens_resolvidos, nao_encontrados)
    """
    produtos = database.listar_produtos()
    resolvidos = []
    nao_encontrados = []

    for qtd, nome_digitado in itens_digitados:
        alvo = nome_digitado.lower()
        encontrado = None
        for p in produtos:
            if alvo == p["nome"].lower() or alvo in p["nome"].lower() or p["nome"].lower() in alvo:
                encontrado = p
                break
        if encontrado:
            resolvidos.append(
                {
                    "produto_id": encontrado["id"],
                    "nome_produto": encontrado["nome"],
                    "quantidade": qtd,
                    "preco_unitario": encontrado["preco"],
                }
            )
        else:
            nao_encontrados.append(nome_digitado)

    return resolvidos, nao_encontrados


def processar_mensagem(telefone, texto):
    """
    Ponto de entrada principal. Retorna a(s) mensagem(ns) de resposta
    (lista de strings) para enviar de volta ao cliente pelo WhatsApp.
    Se o pedido for concluído nesta chamada, retorna também o pedido_id.
    """
    conversa = database.obter_conversa(telefone)
    estado = conversa["estado"]
    dados = json.loads(conversa["dados_temp"] or "{}")
    texto_norm = texto.strip()
    texto_lower = texto_norm.lower()
    pedido_id_criado = None

    # Permite reiniciar o atendimento a qualquer momento
    if texto_lower in ("oi", "olá", "ola", "menu", "cardapio", "cardápio", "começar", "comecar"):
        estado = "aguardando_itens"
        dados = {}
        database.salvar_conversa(telefone, estado, json.dumps(dados))
        return [f"Olá! Bem-vindo(a). 😊\n\n{montar_menu()}"], None

    if estado == "inicio":
        estado = "aguardando_itens"
        database.salvar_conversa(telefone, estado, json.dumps(dados))
        return [f"Olá! Bem-vindo(a). 😊\n\n{montar_menu()}"], None

    if estado == "aguardando_itens":
        itens_digitados = _parse_itens(texto_norm)
        resolvidos, nao_encontrados = _resolver_itens(itens_digitados)

        if not resolvidos:
            return [
                "Não consegui identificar nenhum item do cardápio na sua mensagem. "
                "Pode tentar de novo? Exemplo: _2x X-Burger, 1x Batata Frita_"
            ], None

        # verifica estoque
        sem_estoque = []
        for item in resolvidos:
            produto = database.buscar_produto_por_id(item["produto_id"])
            if produto["estoque_atual"] < item["quantidade"]:
                sem_estoque.append(produto["nome"])

        if sem_estoque:
            return [
                "Infelizmente estamos sem estoque suficiente de: "
                + ", ".join(sem_estoque)
                + ". Pode ajustar seu pedido?"
            ], None

        dados["itens"] = resolvidos
        resumo_linhas = ["Confirmando seu pedido:"]
        total = 0
        for item in resolvidos:
            subtotal = item["quantidade"] * item["preco_unitario"]
            total += subtotal
            resumo_linhas.append(f"- {item['quantidade']}x {item['nome_produto']} (R$ {subtotal:.2f})")
        resumo_linhas.append(f"\n*Total: R$ {total:.2f}*")

        aviso_extra = ""
        if nao_encontrados:
            aviso_extra = (
                "\n\n(Obs: não encontrei no cardápio: " + ", ".join(nao_encontrados) + " — ignorados.)"
            )

        resumo_linhas.append("\n\nEstá correto? Responda *sim* para confirmar ou *não* para refazer o pedido.")
        estado = "aguardando_confirmacao"
        database.salvar_conversa(telefone, estado, json.dumps(dados))
        return ["\n".join(resumo_linhas) + aviso_extra], None

    if estado == "aguardando_confirmacao":
        if texto_lower in ("sim", "s", "confirmar", "confirmo"):
            estado = "aguardando_nome"
            database.salvar_conversa(telefone, estado, json.dumps(dados))
            return ["Ótimo! Qual o nome para o pedido?"], None
        elif texto_lower in ("não", "nao", "n"):
            estado = "aguardando_itens"
            dados = {}
            database.salvar_conversa(telefone, estado, json.dumps(dados))
            return [f"Sem problemas, vamos recomeçar.\n\n{montar_menu()}"], None
        else:
            return ["Por favor, responda *sim* para confirmar ou *não* para refazer o pedido."], None

    if estado == "aguardando_nome":
        dados["cliente_nome"] = texto_norm
        estado = "aguardando_endereco"
        database.salvar_conversa(telefone, estado, json.dumps(dados))
        return ["Perfeito! Qual o endereço de entrega? (ou digite *retirada* se for buscar no balcão)"], None

    if estado == "aguardando_endereco":
        dados["endereco"] = texto_norm
        estado = "aguardando_pagamento"
        database.salvar_conversa(telefone, estado, json.dumps(dados))
        return ["Qual a forma de pagamento? (dinheiro / cartão / pix)"], None

    if estado == "aguardando_pagamento":
        dados["forma_pagamento"] = texto_norm

        pedido_id_criado = database.criar_pedido(
            cliente_telefone=telefone,
            cliente_nome=dados.get("cliente_nome", ""),
            endereco=dados.get("endereco", ""),
            forma_pagamento=dados.get("forma_pagamento", ""),
            itens=dados.get("itens", []),
        )

        database.resetar_conversa(telefone)

        total = sum(i["quantidade"] * i["preco_unitario"] for i in dados.get("itens", []))
        return [
            f"Pedido #{pedido_id_criado} confirmado! ✅\n"
            f"Total: R$ {total:.2f}\n"
            "Já enviamos para a cozinha. Obrigado pela preferência! 🍔"
        ], pedido_id_criado

    # fallback de segurança
    database.resetar_conversa(telefone)
    return [f"Vamos começar de novo.\n\n{montar_menu()}"], None
