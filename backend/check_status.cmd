@echo off
setlocal enabledelayedexpansion

echo ===================================
echo Checking Meeting Minutes Backend Status
echo ===================================
echo.

REM Check if Whisper server is running
echo Checking Whisper server status...
set "WHISPER_RUNNING=0"
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq whisper-server.exe" /fo list ^| findstr "PID:"') do (
    set "WHISPER_PID=%%a"
    set "WHISPER_RUNNING=1"
)

REM Check if Whisper server is listening on port 8178
set "WHISPER_LISTENING=0"
netstat -ano | findstr ":8178.*LISTENING" >nul
if %ERRORLEVEL% equ 0 (
    set "WHISPER_LISTENING=1"
)

REM Check if Python backend is running
echo Checking Python backend status...
set "PYTHON_RUNNING=0"
for /f "tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /fo list ^| findstr "PID:"') do (
    set "PYTHON_PID=%%a"
    set "PYTHON_RUNNING=1"
)

REM Check if Python backend is listening on port 5167
set "PYTHON_LISTENING=0"
netstat -ano | findstr ":5167.*LISTENING" >nul
if %ERRORLEVEL% equ 0 (
    set "PYTHON_LISTENING=1"
)

echo.
echo ===================================
echo Status Report
echo ===================================

if %WHISPER_RUNNING% equ 1 (
    echo Whisper Server: RUNNING (PID: %WHISPER_PID%)
    if %WHISPER_LISTENING% equ 1 (
        echo Whisper Server Port: LISTENING on 8178
    ) else (
        echo Whisper Server Port: NOT LISTENING on 8178 [PROBLEM]
    )
) else (
    echo Whisper Server: NOT RUNNING [PROBLEM]
)

echo.

if %PYTHON_RUNNING% equ 1 (
    echo Python Backend: RUNNING (PID: %PYTHON_PID%)
    if %PYTHON_LISTENING% equ 1 (
        echo Python Backend Port: LISTENING on 5167
    ) else (
        echo Python Backend Port: NOT LISTENING on 5167 [PROBLEM]
    )
) else (
    echo Python Backend: NOT RUNNING [PROBLEM]
)

echo.
echo ===================================
echo Log Files
echo ===================================
echo Whisper Server Log: whisper-server.log
echo Python Backend Log: python-backend.log
echo.

if %WHISPER_RUNNING% equ 0 (
    echo To start Whisper server: start_whisper_server.cmd
)

if %PYTHON_RUNNING% equ 0 (
    echo To start Python backend: start_python_backend.cmd
)

if %WHISPER_RUNNING% equ 0 || %PYTHON_RUNNING% equ 0 (
    echo To start both services: clean_start_backend.cmd
)

echo.
echo ===================================

goto :eof
