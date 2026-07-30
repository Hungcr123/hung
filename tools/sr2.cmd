@echo off
setlocal
set "ROOT=%~dp0.."
set "CONFIG=%~1"
if "%CONFIG%"=="" (
  set "CONFIG=%ROOT%\.agents\sr2_future.yaml"
) else (
  shift
)
uv --project "%ROOT%\tools\sr2" run sr2 "%CONFIG%" %*
