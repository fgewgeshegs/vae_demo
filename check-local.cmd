@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0check-local.ps1"
set EXIT_CODE=%errorlevel%
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Diagnostics found a problem. Press any key to close.
  pause >nul
)
exit /b %EXIT_CODE%
