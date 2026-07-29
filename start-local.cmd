@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-local.ps1"
set EXIT_CODE=%errorlevel%
if "%EXIT_CODE%"=="0" (
  echo.
  echo Project is running successfully.
  echo Open: http://127.0.0.1:5173
  echo You may close this window. The services will keep running.
) else (
  echo.
  echo Startup failed. Read the error above, then press any key to close.
)
echo.
pause
exit /b %EXIT_CODE%
