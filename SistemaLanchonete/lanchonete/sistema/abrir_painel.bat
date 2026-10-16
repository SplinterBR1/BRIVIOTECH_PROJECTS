@echo off
title Painel da Lanchonete
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

echo Iniciando o painel...
start "Painel da Lanchonete - NAO FECHE ESTA JANELA" cmd /k python painel_web.py

timeout /t 3 /nobreak >nul
start "" http://localhost:5001

echo.
echo O painel foi aberto no seu navegador.
echo Para desligar o painel, feche a janela preta "Painel da Lanchonete".
echo Esta janela aqui pode ser fechada.
pause
