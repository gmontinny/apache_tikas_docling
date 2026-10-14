@echo off
echo ========================================
echo  Setup - Apache Tika vs Docling
echo ========================================
echo.

REM Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado.
    echo Baixe em: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python encontrado.

REM Verifica Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Docker nao encontrado.
    echo Baixe em: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)
echo [OK] Docker encontrado.

REM Copia .env se nao existir
if not exist .env (
    copy .env.example .env >nul
    echo [OK] Arquivo .env criado.
) else (
    echo [OK] Arquivo .env ja existe.
)

REM Sobe os containers
echo.
echo Iniciando PostgreSQL e Tika Server...
docker-compose up -d
if errorlevel 1 (
    echo [ERRO] Falha ao iniciar os containers. Verifique se o Docker Desktop esta aberto.
    pause
    exit /b 1
)
echo [OK] Containers iniciados.

REM Instala dependencias Python
echo.
echo Instalando dependencias Python (pode demorar alguns minutos)...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas.

echo.
echo ========================================
echo  Tudo pronto! Para executar, rode:
echo  python src/main.py
echo ========================================
pause
