@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel%==0 (
  python "%~dp0FUTURE_SERVER_2.py" --replace-old %*
) else (
  py -3 "%~dp0FUTURE_SERVER_2.py" --replace-old %*
)

if errorlevel 1 pause
