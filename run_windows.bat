@echo off
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  echo Virtual environment not found. Please follow README setup first.
  pause
  exit /b 1
)
venv\Scripts\python.exe -m waitress --listen=127.0.0.1:5000 app:app
