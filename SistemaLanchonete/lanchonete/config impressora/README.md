# Sistema de Pedidos + Estoque — Lanchonete

Sistema que recebe pedidos pela API oficial do WhatsApp Business (Meta Cloud
API), grava cada pedido como um arquivo JSON e depois um processador em
Python registra o pedido no banco e dá baixa automática no estoque.

## Como funciona (fluxo)

```
Cliente manda mensagem no WhatsApp
        │
        ▼
webhook_whatsapp.py  → recebe via Meta Cloud API, interpreta o texto
        │                e grava um .json em pedidos_pendentes/
        ▼
processador_pedidos.py  → lê o .json, valida estoque, registra no banco
        │                   SQLite, dá baixa no estoque e...
        ├──────────────────────────────┐
        ▼                              ▼
move para pedidos_processados/   enfileira a comanda em
(ou pedidos_erro/ se falhar)     fila_impressao/pendentes/
                                       │
                                       ▼
                            worker_impressao.py → envia para a
                            impressora térmica (ESC/POS), com
                            retentativas automáticas em caso de falha
```

## Arquivos

| Arquivo | Função |
|---|---|
| `database.py` | Cria as tabelas do banco (produtos, pedidos, itens_pedido, movimentação de estoque) |
| `estoque.py` | Funções de consulta, baixa e reposição de estoque |
| `processador_pedidos.py` | Monitora `pedidos_pendentes/`, registra os pedidos e enfileira a comanda para impressão |
| `webhook_whatsapp.py` | Servidor Flask que recebe as mensagens do WhatsApp e gera os arquivos de pedido |
| `impressora.py` | Formata a comanda e envia para a impressora térmica (ESC/POS) |
| `worker_impressao.py` | Monitora a fila de impressão e imprime, com retentativas automáticas |
| `config.py` | Configurações da impressora térmica (tipo de conexão, IP, etc.) |

## 1. Instalação

```bash
pip install -r requirements.txt
python database.py     # cria o banco lanchonete.db e produtos de exemplo
```

## 2. Configurar a API oficial do WhatsApp Business (Meta Cloud API)

1. Crie um app no [Meta for Developers](https://developers.facebook.com/) e
   ative o produto **WhatsApp**.
2. Anote o **número de telefone de teste** (ou o número comercial já
   verificado) e o **access token** gerado.
3. Defina um `VERIFY_TOKEN` (uma senha qualquer que você escolhe), por
   exemplo:
   ```bash
   export VERIFY_TOKEN="minha_senha_secreta"
   ```
4. Rode o webhook localmente:
   ```bash
   python webhook_whatsapp.py
   ```
5. Como a Meta exige uma URL pública (HTTPS) para o webhook, exponha sua
   porta local com uma ferramenta como `ngrok`:
   ```bash
   ngrok http 5000
   ```
6. No painel da Meta, em **WhatsApp > Configuration > Webhook**, cadastre:
   - **Callback URL**: `https://SEU-DOMINIO-NGROK/webhook`
   - **Verify Token**: o mesmo valor de `VERIFY_TOKEN`
   - Inscreva-se no campo `messages`.

## 3. Rodar o processador de pedidos

Em outro terminal, deixe rodando continuamente:

```bash
python processador_pedidos.py
```

Ele verifica a pasta `pedidos_pendentes/` a cada 3 segundos.

## 4. Formato de mensagem que o cliente deve enviar

```
PEDIDO
2x X-Burger
1x Refrigerante Lata
```

O parser aceita `2x Produto`, `2 x Produto` ou `2 Produto`. Os nomes dos
produtos devem bater com o cadastro em `database.py` (ajuste conforme seu
cardápio real).

## 5. Testar sem depender do WhatsApp

Você pode simular um pedido criando o JSON manualmente na pasta
`pedidos_pendentes/`:

```json
{
  "pedido_id": "PED-TESTE-0001",
  "cliente": {"nome": "Teste", "telefone": "5515999999999"},
  "itens": [
    {"produto": "X-Burger", "quantidade": 2, "preco_unit": 18.00}
  ],
  "total": 36.00,
  "status": "pendente",
  "timestamp": "2026-07-24T12:00:00"
}
```

Depois rode `python processador_pedidos.py --once` para processar tudo que
estiver pendente e encerrar.

## 6. Comanda automática na impressora térmica

Assim que um pedido é registrado com sucesso, a comanda é automaticamente
colocada na fila (`fila_impressao/pendentes/`). Um processo separado,
`worker_impressao.py`, envia essa fila para a impressora térmica usando o
protocolo ESC/POS (biblioteca `python-escpos`), com retentativas
automáticas em caso de falha de conexão.

### Rodar o worker de impressão

Em outro terminal (além do `processador_pedidos.py`):

```bash
python worker_impressao.py
```

### Configurar a impressora (`config.py`)

Por padrão o sistema está em **modo de teste** (`IMPRESSORA_MODO_TESTE = True`),
que só mostra a comanda formatada no console — sem precisar de hardware.
Quando a impressora estiver disponível:

1. Abra `config.py` e mude `IMPRESSORA_MODO_TESTE` para `False`.
2. Escolha `IMPRESSORA_TIPO`:
   - `"rede"` — impressora térmica com IP na rede (mais comum em lanchonetes).
     Configure `IMPRESSORA_IP` e `IMPRESSORA_PORTA` (geralmente `9100`).
   - `"usb"` — impressora conectada por USB. Configure `IMPRESSORA_VENDOR_ID`
     e `IMPRESSORA_PRODUCT_ID` (descubra com `lsusb` no Linux).
   - `"serial"` — impressora conectada por porta serial/COM. Configure
     `IMPRESSORA_PORTA_SERIAL` e `IMPRESSORA_BAUDRATE`.
3. Instale a dependência: `pip install python-escpos` (já está no
   `requirements.txt`).

### Retentativas e falhas

- Se a impressão falhar (impressora desligada, sem papel, rede fora), o
  worker tenta novamente automaticamente até `MAX_TENTATIVAS_IMPRESSAO`
  vezes (padrão: 3).
- Depois disso, a comanda vai para `fila_impressao/erro/` para não travar
  a fila.
- Para reenviar manualmente as comandas que falharam:
  ```bash
  python worker_impressao.py --reenviar-erros
  ```

## 7. Gerenciar estoque

```python
from estoque import repor_estoque, listar_estoque_baixo, listar_estoque_completo

repor_estoque("X-Burger", 20)      # dá entrada de 20 unidades
listar_estoque_baixo()             # produtos no ou abaixo do estoque mínimo
listar_estoque_completo()          # visão geral do cardápio
```

## Próximos passos sugeridos

- Enviar mensagem de confirmação/erro de volta ao cliente via WhatsApp
  (usar a API de envio da Meta Cloud API — os pontos `TODO` no código
  já indicam onde plugar isso).
- Trocar o polling de 3 em 3 segundos por um watcher de sistema de
  arquivos (`watchdog`) para reação instantânea.
- Adicionar autenticação/painel web para consultar pedidos e estoque.
- Rodar `processador_pedidos.py` e `worker_impressao.py` como serviços
  (systemd, supervisor, etc.) para reiniciar automaticamente se caírem.
