@echo off
echo ====================================
echo Power Gallery - Installation
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
echo Creation du raccourci...
set SCRIPT_DIR=%~dp0

> "%TEMP%\make_shortcut.vbs" echo Set ws = CreateObject("WScript.Shell")
>> "%TEMP%\make_shortcut.vbs" echo Set s = ws.CreateShortcut("%SCRIPT_DIR%Power Gallery.lnk")
>> "%TEMP%\make_shortcut.vbs" echo s.TargetPath = "%SCRIPT_DIR%START.BAT"
>> "%TEMP%\make_shortcut.vbs" echo s.WorkingDirectory = "%SCRIPT_DIR%"
>> "%TEMP%\make_shortcut.vbs" echo s.IconLocation = "%SCRIPT_DIR%assets/powergallery.ico"
>> "%TEMP%\make_shortcut.vbs" echo s.WindowStyle = 7
>> "%TEMP%\make_shortcut.vbs" echo s.Save()

cscript //nologo "%TEMP%\make_shortcut.vbs"
del "%TEMP%\make_shortcut.vbs"

echo.
echo ====================================
echo Installation terminee !
echo ====================================
echo.
echo Lancez "Power Gallery.lnk" ou START.BAT pour demarrer l'application
pause