@echo off
title Indicador Docente
color 0A

echo ========================================================
echo   Iniciando el Sistema de Indicador Docente
echo   Por favor, espere un momento...
echo ========================================================

:: 0. Validacion de credenciales
if not exist ".env" (
    if exist "plantilla_credenciales.txt" (
        echo [INFO] Configurando credenciales del sistema...
        ren "plantilla_credenciales.txt" ".env"
    ) else (
        echo [ERROR] No se encontro el archivo de credenciales.
        echo Por favor, asegurese de tener el archivo 'plantilla_credenciales.txt' completado con sus datos en esta misma carpeta.
        pause
        exit
    )
)

:: 1. Creacion del entorno virtual (primera ejecucion)
if not exist "entorno_profe" (
    echo [INFO] Configurando el entorno de ejecucion por primera vez. 
    echo [INFO] Este proceso puede demorar unos minutos, no cierre la ventana...
    python -m venv entorno_profe
)

:: 2. Activacion del entorno virtual
call entorno_profe\Scripts\activate

:: 3. Instalacion de dependencias de Python
echo [INFO] Verificando e instalando requerimientos de sistema (1/2)...
pip install -q -r requirements.txt

:: 4. Instalacion de dependencias de Node.js
echo [INFO] Verificando e instalando requerimientos de sistema (2/2)...
call npm install --silent

:: 5. Ejecucion principal
echo [INFO] Sistema configurado correctamente. Abriendo la interfaz...
python main.py

pause