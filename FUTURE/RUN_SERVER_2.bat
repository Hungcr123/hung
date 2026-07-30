@echo off
setlocal
cd /d "%~dp0.."
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0server2\run_server_2.py" %*
) else (
  python "%~dp0server2\run_server_2.py" %*
)
if errorlevel 1 pause
