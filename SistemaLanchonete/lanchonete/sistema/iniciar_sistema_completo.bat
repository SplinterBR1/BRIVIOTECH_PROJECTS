@echo off
title Sistema da Lanchonete
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo [ERRO] O Python nao foi encontrado neste computador.
    echo Instale em https://python.org/downloads e marque a opcao
    echo "Add Python to PATH" durante a instalacao. Depois tente de novo.
    echo.
    pause
    exit /b
)

echo Verificando dependencias (isso so demora na primeira vez)...
python -m pip install -r requirements.txt --quiet

echo Iniciando o sistema completo...
start "Processador de Pedidos - NAO FECHE" cmd /k python processador_pedidos.py
start "Fila de Impressao - NAO FECHE" cmd /k python worker_impressao.py
start "Painel Web - NAO FECHE" cmd /k python painel_web.py

timeout /t 3 /nobreak >nul
start "" http://localhost:5001

echo.
echo Tudo ligado! Tres janelas pretas foram abertas - deixe elas abertas
echo enquanto a lanchonete estiver funcionando. O painel abriu no navegador.
echo.
echo (O recebimento de mensagens do WhatsApp e configurado a parte,
echo  veja o README.md, secao 2.)
echo.
echo Esta janela aqui pode ser fechada.
pause
