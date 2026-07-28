@echo off
REM =========================================================
REM  Gera o executavel do Sistema da Lanchonete para Windows.
REM  Rode este arquivo dando 2 cliques nele, ou pelo terminal:
REM      build_windows.bat
REM
REM  Pre-requisito: Python 3.10+ instalado e marcado a opcao
REM  "Add python.exe to PATH" durante a instalacao.
REM  (baixe em https://www.python.org/downloads/windows/)
REM =========================================================

setlocal

echo.
echo === Criando ambiente virtual (venv) ===
python -m venv venv
if errorlevel 1 (
    echo ERRO: nao encontrei o comando "python". Instale o Python e tente de novo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo === Instalando dependencias ===
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo.
echo === Gerando o executavel (isso pode demorar alguns minutos) ===
pyinstaller --noconfirm --onefile --windowed --name "SistemaLanchonete" main.py

echo.
echo =========================================================
echo  Pronto! O executavel esta em: dist\SistemaLanchonete.exe
echo.
echo  IMPORTANTE: copie o SistemaLanchonete.exe para uma pasta
echo  fixa (ex.: Area de Trabalho\SistemaLanchonete\) e rode-o
echo  a partir dai. O banco de dados (lanchonete.db) e a pasta
echo  de comandas serao criados ao lado do .exe.
echo =========================================================
echo.
pause
