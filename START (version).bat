@echo off

echo ====================================
echo Checkpoints Gallery PyQt6
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

REM Detect folder version (v2, v3, v4, etc.)
for %%I in (.) do set FOLDER_NAME=%%~nxI
set SCRIPT_NAME=checkpoints_gallery_%FOLDER_NAME%.py

REM Check if versioned script exists
if not exist %SCRIPT_NAME% (
    echo [INFO] %SCRIPT_NAME% non trouvé
    set SCRIPT_NAME=checkpoints_gallery.py
)

echo Lancement de %SCRIPT_NAME%
echo.

REM Launch app - no console
REM start "" venv\Scripts\pythonw.exe %SCRIPT_NAME%

REM DEBUG - Launch app with console that closes on normal exit
call venv\Scripts\activate.bat
python %SCRIPT_NAME%
if errorlevel 1 (
    echo.
    echo ================================================
    echo ERREUR: L'application s'est terminee avec une erreur
    echo ================================================
    pause
) else (
    REM Normal exit - close automatically
    exit
)
