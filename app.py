# app.py

import os
import hashlib
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from flask import Flask, request, jsonify

app = Flask(__name__)


# Lê as URLs de conexão do ambiente


DATABASE_URL_OLTP = os.environ.get("DATABASE_URL")
DATABASE_URL_DW   = os.environ.get("DATABASE_URL_DW")

#necessario dar export com a senha do db
if not DATABASE_URL_OLTP:
    raise RuntimeError("Defina a variável de ambiente DATABASE_URL antes de executar.")
if not DATABASE_URL_DW:
    raise RuntimeError("Defina a variável de ambiente DATABASE_URL_DW antes de executar.")

def get_conn_oltp():
    return psycopg2.connect(DATABASE_URL_OLTP, sslmode="require")

def get_conn_dw():
    return psycopg2.connect(DATABASE_URL_DW, sslmode="require")



# 1) ROTA: Criar Conta no OLTP

@app.route("/criarConta", methods=["POST"])
def criar_conta():
    data = request.get_json()
    email = data.get("email")
    senha = data.get("senha")
    nome  = data.get("nome")
    if not (email and senha and nome):
        return jsonify({"error": "email, senha e nome obrigatórios"}), 400

    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    conn = get_conn_oltp()
    cur = conn.cursor()
    # Verifica se já existe
    cur.execute("SELECT id FROM ecommerce.users WHERE email = %s", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return jsonify({"error": "Email já cadastrado"}), 400

    # Insere
    cur.execute(
        """
        INSERT INTO ecommerce.users (email, senha_hash, nome)
        VALUES (%s, %s, %s)
        RETURNING id, email, nome, data_criacao
        """,
        (email, senha_hash, nome)
    )
    novo = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "id": novo[0],
        "email": novo[1],
        "nome": novo[2],
        "data_criacao": novo[3].isoformat()
    }), 201



# 2) ROTA: Login (básico)

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    senha = data.get("senha")
    if not (email and senha):
        return jsonify({"error": "email e senha obrigatórios"}), 400

    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    conn = get_conn_oltp()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, nome FROM ecommerce.users WHERE email = %s AND senha_hash = %s",
        (email, senha_hash)
    )
    user = cur.fetchone()
    cur.close()
    conn.close()
    if not user:
        return jsonify({"error": "credenciais inválidas"}), 401

    return jsonify({"id": user[0], "nome": user[1]}), 200



# 3) ROTA: Criar Pedido no OLTP

@app.route("/criarPedido", methods=["POST"])
def criar_pedido():
    data = request.get_json()
    user_id = data.get("user_id")
    itens   = data.get("itens")
    if not (user_id and isinstance(itens, list)):
        return jsonify({"error": "user_id e itens obrigatórios"}), 400

    conn = get_conn_oltp()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1) Insere o pedido (status PENDENTE)
    cur.execute(
        """
        INSERT INTO ecommerce.orders (user_id, status, valor_total)
        VALUES (%s, 'PENDENTE', 0)
        RETURNING id, data_pedido
        """,
        (user_id,)
    )
    pedido = cur.fetchone()
    pedido_id = pedido["id"]

    total = 0
    # 2) Insere itens e atualiza estoque
    for item in itens:
        pid = item.get("product_id")
        qtd = item.get("quantidade", 0)
        if not (pid and qtd > 0):
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": "item inválido"}), 400

        cur.execute(
            "SELECT preco_unitario, estoque FROM ecommerce.products WHERE id = %s",
            (pid,)
        )
        prod = cur.fetchone()
        if not prod:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": f"Produto {pid} não encontrado"}), 404
        if prod["estoque"] < qtd:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": f"Estoque insuficiente para produto {pid}"}), 400

        subtotal = float(prod["preco_unitario"]) * qtd
        total += subtotal

        cur.execute(
            """
            INSERT INTO ecommerce.order_items (order_id, product_id, quantidade, preco_unitario)
            VALUES (%s, %s, %s, %s)
            """,
            (pedido_id, pid, qtd, prod["preco_unitario"])
        )
        cur.execute(
            "UPDATE ecommerce.products SET estoque = estoque - %s WHERE id = %s",
            (qtd, pid)
        )

    # 3) Atualiza valor_total
    cur.execute(
        "UPDATE ecommerce.orders SET valor_total = %s WHERE id = %s",
        (total, pedido_id)
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "pedido_id": pedido_id,
        "valor_total": total,
        "data_pedido": pedido["data_pedido"].isoformat()
    }), 201



# 4) ROTA: Faturar Pedido e disparar ETL

@app.route("/faturar/<int:pedido_id>", methods=["POST"])
def faturar_pedido(pedido_id):
    # (1) Conexão OLTP
    conn_oltp = get_conn_oltp()
    cur_oltp  = conn_oltp.cursor(cursor_factory=RealDictCursor)

    # 2) Verifica se o pedido existe e está PENDENTE
    cur_oltp.execute("SELECT * FROM ecommerce.orders WHERE id = %s", (pedido_id,))
    pedido = cur_oltp.fetchone()
    if not pedido:
        cur_oltp.close()
        conn_oltp.close()
        return jsonify({"error": "Pedido não encontrado"}), 404
    if pedido["status"] == "FATURADO":
        cur_oltp.close()
        conn_oltp.close()
        return jsonify({"error": "Pedido já faturado"}), 400

    # 3) Marca como FATURADO
    cur_oltp.execute(
        "UPDATE ecommerce.orders SET status = 'FATURADO' WHERE id = %s RETURNING data_pedido, user_id, valor_total",
        (pedido_id,)
    )
    atualizado = cur_oltp.fetchone()

    # 4) Extrai dados do usuário
    user_id = atualizado["user_id"]
    cur_oltp.execute(
        "SELECT id, email, nome, data_criacao FROM ecommerce.users WHERE id = %s",
        (user_id,)
    )
    usuario = cur_oltp.fetchone()

    # 5) Extrai itens + dados de produto
    cur_oltp.execute("""
        SELECT oi.product_id,
               oi.quantidade,
               oi.preco_unitario,
               p.nome       AS nome_produto,
               p.descricao  AS descricao_produto
        FROM ecommerce.order_items oi
        JOIN ecommerce.products p ON oi.product_id = p.id
        WHERE oi.order_id = %s
    """, (pedido_id,))
    itens = cur_oltp.fetchall()

    # 6) Monta JSON
    documento = {
        "pedido": {
            "id":          pedido_id,
            "status":     "FATURADO",
            "valor_total": float(atualizado["valor_total"]),
            "data_pedido": atualizado["data_pedido"].isoformat()
        },
        "usuario": {
            "id":           usuario["id"],
            "email":        usuario["email"],
            "nome":         usuario["nome"],
            "data_criacao": usuario["data_criacao"].isoformat()
        },
        "itens": []
    }
    for i in itens:
        documento["itens"].append({
            "product_id":     i["product_id"],
            "nome_produto":   i["nome_produto"],
            "descricao":      i["descricao_produto"],
            "quantidade":     i["quantidade"],
            "preco_unitario": float(i["preco_unitario"]),
            "subtotal":       float(i["preco_unitario"]) * i["quantidade"]
        })

    # 7) Fecha cursor/conn OLTP
    cur_oltp.close()
    conn_oltp.commit()
    conn_oltp.close()

    # 8) Insere no DW
    conn_dw = get_conn_dw()
    cur_dw  = conn_dw.cursor()
    cur_dw.execute(
        """
        INSERT INTO dw_minhaempresa.fato_pedidos
            (pedido_id, user_id, data_faturamento, documento)
        VALUES (%s, %s, NOW(), %s)
        """,
        (pedido_id, user_id, Json(documento))
    )
    conn_dw.commit()
    cur_dw.close()
    conn_dw.close()

    # 9) Retorna JSON completo
    return jsonify(documento), 200



# 5) Adicionar produto (no OLTP)

@app.route("/addProduto", methods=["POST"])
def add_produto():
    data = request.get_json()
    nome      = data.get("nome")
    descricao = data.get("descricao", "")
    preco     = data.get("preco_unitario")
    estoque   = data.get("estoque", 0)
    if not (nome and preco is not None):
        return jsonify({"error": "nome e preco_unitario obrigatórios"}), 400

    conn = get_conn_oltp()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ecommerce.products (nome, descricao, preco_unitario, estoque)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (nome, descricao, preco, estoque)
    )
    novo = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"product_id": novo}), 201



if __name__ == "__main__":

    app.run(debug=True)
