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

REM Launch app - no console
REM start "" venv\Scripts\pythonw.exe checkpoints_gallery.py

REM DEBUG - Launch app with the console
call venv\Scripts\activate.bat
python power_gallery.py
pause