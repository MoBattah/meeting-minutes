@echo off
setlocal enabledelayedexpansion

REM Default port
set "PORT=5167"
if "%~1" neq "" (
    set "PORT=%~1"
)

echo Starting Meeting Minutes Backend with visible output...
echo Port: %PORT%
echo.

REM Run the PowerShell script
powershell -ExecutionPolicy Bypass -File start_with_output.ps1 %PORT%

goto :eof
