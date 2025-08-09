# API E-commerce OLTP + Data Warehouse

<!-- Badges -->

![Last Commit](https://img.shields.io/github/last-commit/jpedro0807/ETL_dw?style=flat-square)
![Python 100%](https://img.shields.io/badge/Python-100%25-blue?style=flat-square\&logo=python)
![Languages](https://img.shields.io/github/languages/count/jpedro0807/ETL_dw?tyle=flat-square)

## Descrição

**API REST** desenvolvida em **Flask** para simular um fluxo básico de **e-commerce**, integrando um banco de dados **OLTP** para operações transacionais e um **Data Warehouse (DW)** para armazenamento analítico.

O projeto inclui:

* Cadastro e autenticação de usuários.
* Gerenciamento de produtos.
* Criação e faturamento de pedidos.
* Registro automático de pedidos faturados no DW.

## Tecnologias Utilizadas

* **Linguagem**: Python 3.10+
* **Framework**: Flask
* **Banco de Dados**: PostgreSQL (OLTP e DW)
* **Bibliotecas**: psycopg2, Flask, Json (PostgreSQL)

## Estrutura do Projeto

```
/ (raiz do projeto)
├── app.py                 # Código principal da API Flask
├── requirements.txt       # Dependências do projeto
└── README.md              # Guia de uso e documentação
```

## Como Configurar e Executar

1. **Clonar o repositório**

   ```bash
   git clone https://github.com/jpedro0807/ETL_dw.git
   cd seu-repositorio
   ```

2. **Criar ambiente virtual e instalar dependências**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate    # Windows

   pip install -r requirements.txt
   ```

3. **Definir variáveis de ambiente**

   ```bash
   export DATABASE_URL="postgresql://usuario:senha@host:porta/db_oltp"
   export DATABASE_URL_DW="postgresql://usuario:senha@host:porta/db_dw"
   ```

4. **Executar**

   ```bash
   python app.py
   ```

   Por padrão, a aplicação roda em `http://127.0.0.1:5000`

---

## Funcionalidades e Exemplos de Uso

### **1️⃣ Criar Conta**

```http
POST /criarConta
Content-Type: application/json

{
  "email": "teste@exemplo.com",
  "senha": "123456",
  "nome": "João"
}
```

**Resposta:**

```json
{
  "id": 1,
  "email": "teste@exemplo.com",
  "nome": "João",
  "data_criacao": "2025-08-08T14:32:10"
}
```

---

### **2️⃣ Login**

```http
POST /login
Content-Type: application/json

{
  "email": "teste@exemplo.com",
  "senha": "123456"
}
```

**Resposta:**

```json
{
  "id": 1,
  "nome": "João"
}
```

---

### **3️⃣ Adicionar Produto**

```http
POST /addProduto
Content-Type: application/json

{
  "nome": "Mouse Gamer",
  "descricao": "Mouse com 7 botões",
  "preco_unitario": 150.0,
  "estoque": 20
}
```

**Resposta:**

```json
{
  "product_id": 1
}
```

---

### **4️⃣ Criar Pedido**

```http
POST /criarPedido
Content-Type: application/json

{
  "user_id": 1,
  "itens": [
    {"product_id": 1, "quantidade": 2},
    {"product_id": 2, "quantidade": 1}
  ]
}
```

**Resposta:**

```json
{
  "pedido_id": 1,
  "valor_total": 350.0,
  "data_pedido": "2025-08-08T15:00:12"
}
```

---

### **5️⃣ Faturar Pedido**

```http
POST /faturar/1
```

**Resposta:**

```json
{
  "pedido": {
    "id": 1,
    "status": "FATURADO",
    "valor_total": 350.0,
    "data_pedido": "2025-08-08T15:00:12"
  },
  "usuario": {
    "id": 1,
    "email": "teste@exemplo.com",
    "nome": "João",
    "data_criacao": "2025-08-08T14:32:10"
  },
  "itens": [
    {
      "product_id": 1,
      "nome_produto": "Mouse Gamer",
      "descricao": "Mouse com 7 botões",
      "quantidade": 2,
      "preco_unitario": 150.0,
      "subtotal": 300.0
    },
    {
      "product_id": 2,
      "nome_produto": "Teclado Mecânico",
      "descricao": "Teclado RGB",
      "quantidade": 1,
      "preco_unitario": 50.0,
      "subtotal": 50.0
    }
  ]
}
```

---


## Contato

* **Nome**: \Joao Pedro Barbosa da Silva
* **Email**: \[[jpedro080@hotmail.com](mailto:jpedro080@hotmail.com)]
* **LinkedIn**: \[[https://www.linkedin.com/in/jpedro0807/](https://www.linkedin.com/in/jpedro0807/)]

> Este projeto demonstra conhecimentos em desenvolvimento de APIs com Flask, integração entre sistemas OLTP e DW, manipulação de dados em PostgreSQL e boas práticas de arquitetura de software.
