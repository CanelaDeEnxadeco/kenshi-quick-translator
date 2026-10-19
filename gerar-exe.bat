@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo from kenshi_quick_translator.cli import main> iniciar.py
echo raise SystemExit(main(["gui"]))>> iniciar.py
python -m pip install pyinstaller
python -m pip install pillow
python -m pip install .
rem --noupx: sem compressao UPX (ela e a causa mais comum de alerta falso em antivirus)
python -m PyInstaller --noconfirm --clean --onefile --windowed --noupx --name KenshiQuickTranslator --icon "kenshi_quick_translator\icone.ico" --collect-all kenshi_translator_toolkit --hidden-import kenshi_quick_translator.gui --hidden-import tkinter --hidden-import PIL.ImageTk --add-data "kenshi_quick_translator\default_glossary.json;kenshi_quick_translator" --add-data "kenshi_quick_translator\icone.ico;kenshi_quick_translator" --add-data "kenshi_quick_translator\icone.png;kenshi_quick_translator" iniciar.py
if errorlevel 1 (
  echo.
  echo Deu erro ao gerar o programa. Veja as mensagens acima.
  pause
  exit /b 1
)

rem Pasta pronta para distribuir: so o .exe e os textos, sem codigo-fonte.
if exist lancamento rmdir /s /q lancamento
mkdir lancamento\KenshiQuickTranslator
copy /y dist\KenshiQuickTranslator.exe lancamento\KenshiQuickTranslator\ >nul
copy /y LEIA-ME-lancamento.txt lancamento\KenshiQuickTranslator\LEIA-ME.txt >nul
copy /y LICENSE lancamento\KenshiQuickTranslator\ >nul
copy /y LICENCAS-TERCEIROS.txt lancamento\KenshiQuickTranslator\ >nul
echo.
echo Pronto: lancamento\KenshiQuickTranslator\ (KenshiQuickTranslator.exe + LEIA-ME + licencas)
pause
