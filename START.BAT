@echo off
echo ====================================
echo  Checkpoints Gallery PyQt6
echo ====================================
echo.

REM Check if venv exists
if not exist venv (
    echo [ERREUR] Environnement virtuel non trouve
    echo.
    echo Veuillez d'abord executer INSTALL.BAT
    echo.
    pause
    exit /b 1
)

REM ::DEBUG - Launch app with the console
REM call venv\Scripts\activate.bat
REM python power_gallery.py
REM pause

REM ::Launch app - no console
start "" venv\Scripts\pythonw.exe power_gallery.py