@echo off
echo ====================================
echo Checkpoints Gallery - Installation
echo ====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Python n'est pas installe ou pas dans le PATH
    echo Telechargez Python sur https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Creation du venv...
python -m venv venv

echo.
echo Activation du venv...
call venv\Scripts\activate.bat

echo.
echo Installation de PyQt6...
pip install PyQt6

echo.
echo ====================================
echo Installation terminee !
echo ====================================
echo.
echo Lancez START.BAT pour demarrer l'application
pause
