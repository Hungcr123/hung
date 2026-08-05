@echo off
setlocal EnableExtensions

cd /d "%~dp0"

if not exist "%CD%\run" mkdir "%CD%\run"

echo Starting FutureWorkerAuto Build Monitor...
echo.

python "%CD%\build_future_worker_auto.py"
if errorlevel 1 (
  echo.
  echo Build failed. Check:
  echo %CD%\run\future_worker_auto_rebuild_latest.err.log
  pause
  exit /b 1
)

echo.
echo Build complete. Output:
echo %CD%\dist_worker\FutureWorkerAuto.exe
