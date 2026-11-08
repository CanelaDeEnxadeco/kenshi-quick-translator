@echo off
cd /d "%~dp0"
python -m unittest tests.test_window_languages -v
pause
