# Sistema da Lanchonete — Pedidos via WhatsApp + Comanda na Impressora Térmica

Sistema simples com interface gráfica que:

1. Recebe pedidos pelo WhatsApp através de um chatbot (máquina de estados).
2. Guarda tudo em um banco SQLite local (`lanchonete.db`).
3. Baixa o estoque automaticamente quando um pedido é fechado.
4. Envia a comanda para a impressora térmica (USB, rede ou modo teste em arquivo).
5. Mostra pedidos e estoque em uma interface gráfica (Tkinter), com botões
   para avançar o status do pedido e reimprimir a comanda.

## Estrutura dos arquivos

```
sistema_lanchonete/
├── main.py          # ponto de entrada: sobe o webhook + abre a interface gráfica
├── config.py         # tokens, banco de dados e configuração da impressora
├── database.py        # acesso ao SQLite (produtos, pedidos, itens, conversas)
├── chatbot.py          # máquina de estados da conversa do WhatsApp
├── webhook.py           # servidor Flask que recebe/envia mensagens do WhatsApp
├── impressora.py          # geração e envio da comanda para a impressora térmica
├── gui.py                  # interface gráfica (abas Pedidos e Estoque)
└── requirements.txt
```

## 1. Instalação

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

No Linux, se o Tkinter não vier instalado com o Python:
```bash
sudo apt install python3-tk
```

Se você **não** for usar impressora USB, pode remover `python-escpos` do
`requirements.txt` sem problemas (o modo "arquivo" não depende dela).

## 2. Configurar o WhatsApp Business (Cloud API)

1. Crie uma conta em https://developers.facebook.com/ e um app do tipo
   "Business", ativando o produto **WhatsApp**.
2. No painel do WhatsApp, gere um **token de acesso** (para começar pode
   usar o token temporário de teste; para produção, gere um token
   permanente com uma System User).
3. Copie o **Phone Number ID** exibido no painel.
4. Preencha em `config.py` (ou defina como variáveis de ambiente):
   - `WHATSAPP_TOKEN`
   - `WHATSAPP_PHONE_NUMBER_ID`
   - `WHATSAPP_VERIFY_TOKEN` (uma palavra qualquer, escolhida por você)
5. Como a Meta precisa alcançar seu webhook pela internet, exponha a porta
   local (padrão 5000) com um túnel, por exemplo:
   ```bash
   ngrok http 5000
   ```
6. No painel da Meta, configure o webhook apontando para
   `https://SEU-TUNEL/webhook`, usando o mesmo `WHATSAPP_VERIFY_TOKEN`, e
   inscreva-se no campo `messages`.

## 3. Configurar a impressora térmica

Em `config.py`, ajuste `IMPRESSORA_TIPO`:

- `"arquivo"` (padrão): não precisa de impressora — grava cada comanda em
  um `.txt` dentro da pasta `comandas/`. Ótimo para testar o sistema.
- `"usb"`: preencha `IMPRESSORA_USB_VENDOR_ID` e `IMPRESSORA_USB_PRODUCT_ID`
  (descubra com `lsusb` no Linux). Requer a biblioteca `python-escpos` e,
  em alguns casos, permissões de acesso à porta USB (regra `udev`).
- `"rede"`: preencha `IMPRESSORA_REDE_IP` com o IP da impressora (a
  maioria escuta na porta 9100, já configurada por padrão).

## 4. Rodando o sistema

```bash
python main.py
```

Isso abre a janela do sistema (abas **Pedidos** e **Estoque**) e, em
paralelo, inicia o servidor que recebe as mensagens do WhatsApp na porta
5000. Assim que um pedido é fechado pelo cliente no WhatsApp, ele aparece
automaticamente na aba Pedidos (atualização a cada poucos segundos) e a
comanda é enviada para a impressora.

## 5. Gerando o executável (.exe) para Windows

O `.exe` precisa ser gerado **numa máquina Windows** (o PyInstaller empacota
para o sistema operacional em que ele é executado — não é possível gerar um
`.exe` do Windows a partir de outro sistema). O processo é simples:

1. Copie a pasta inteira `sistema_lanchonete` para o computador Windows da
   lanchonete.
2. Se ainda não tiver, instale o Python em https://www.python.org/downloads/windows/
   — na tela de instalação, marque a caixa **"Add python.exe to PATH"**.
3. Preencha `config.py` com o token do WhatsApp e o tipo de impressora
   (veja as seções 2 e 3 acima) **antes** de gerar o executável.
4. Dê duplo clique em `build_windows.bat` (ou rode-o pelo Prompt de
   Comando). Ele vai:
   - criar um ambiente virtual,
   - instalar as dependências e o PyInstaller,
   - gerar `dist\SistemaLanchonete.exe`.
5. Copie `SistemaLanchonete.exe` para uma pasta fixa (ex.:
   `Área de Trabalho\SistemaLanchonete\`) e rode-o a partir dali — o banco
   de dados (`lanchonete.db`) e a pasta `comandas\` serão criados ao lado
   do `.exe`, então não mova o executável sozinho depois de já ter pedidos
   salvos.
6. Se o Windows Defender/SmartScreen avisar "Windows protegeu o
   computador" (comum em `.exe` sem assinatura digital), clique em
   "Mais informações" → "Executar assim mesmo".

Quer atalho na área de trabalho? Clique com o botão direito no
`SistemaLanchonete.exe` → **Enviar para → Área de trabalho (criar atalho)**.

## 6. Como testar um pedido sem usar o WhatsApp de verdade

Você não precisa ter a integração com o WhatsApp configurada para testar o
resto do sistema. Duas opções:

**A) Pelo botão na interface gráfica**
Na aba **Pedidos**, clique em **"➕ Criar pedido de teste"**. Isso cria um
pedido fictício com itens aleatórios do seu estoque, baixa o estoque e já
manda a comanda para a impressora (ou gera o `.txt` em `comandas/`, se o
modo estiver em `"arquivo"`). Ótimo para testar rapidamente a impressora e
o fluxo de status dos pedidos.

**B) Pelo terminal, simulando a conversa inteira do WhatsApp**
```bash
python simular_pedido.py
```
Roda automaticamente uma conversa de exemplo (oi → escolhe itens → confirma
→ nome → endereço → pagamento) e mostra as respostas do bot no terminal,
igual apareceria no WhatsApp. Depois é só abrir/atualizar a interface
gráfica para ver o pedido na lista.

Se quiser digitar você mesmo cada mensagem (para testar frases diferentes,
nomes de produtos escritos de outro jeito, etc.):
```bash
python simular_pedido.py --manual
```

## 7. Como o cliente pede pelo WhatsApp

1. Cliente manda "oi" → recebe o cardápio.
2. Cliente manda algo como `2x X-Burger, 1x Batata Frita, 1x Refrigerante Lata`.
3. Bot confirma o resumo e o total → cliente responde "sim".
4. Bot pergunta nome, endereço (ou "retirada") e forma de pagamento.
5. Pedido é criado, estoque é baixado e a comanda é impressa.

## Personalizações fáceis

- **Cardápio**: edite direto pela aba Estoque da interface gráfica, ou
  ajuste a lista `produtos_exemplo` em `database.py` (só vale na primeira
  vez que o banco é criado).
- **Layout da comanda**: função `_texto_comanda` em `impressora.py`.
- **Textos do chatbot**: `chatbot.py`.

## Limitações desta versão

- O reconhecimento dos itens do pedido é por comparação de texto simples
  (não usa IA); nomes muito diferentes do cadastrado podem não ser
  reconhecidos.
- Pensado para um único atendente/computador rodando a interface gráfica.
- Não lida com pagamento online — apenas registra a forma escolhida.
