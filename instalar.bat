@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instalando o Kenshi Quick Translator...
python -m pip install --upgrade pip
python -m pip install .
python -m pip install pillow
if errorlevel 1 (
  echo.
  echo Deu erro. Confira se o Python esta instalado e marcado em "Add python.exe to PATH".
) else (
  echo.
  echo Pronto! Agora use o abrir.bat.
)
pause
