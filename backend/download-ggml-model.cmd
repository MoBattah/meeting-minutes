@echo off

pushd %~dp0
set models_path=%CD%
for %%d in (%~dp0..) do set root_path=%%~fd
popd

set models=tiny.en tiny base.en base small.en small medium.en medium large-v1 large-v2 large-v3 large-v3-turbo tiny-q5_1 tiny.en-q5_1 tiny-q8_0 base-q5_1 base.en-q5_1 base-q8_0 small.en-tdrz small-q5_1 small.en-q5_1 small-q8_0 medium-q5_0 medium.en-q5_0 medium-q8_0 large-v2-q5_0 large-v2-q8_0 large-v3-q5_0 large-v3-turbo-q5_0 large-v3-turbo-q8_0

set argc=0
for %%x in (%*) do set /A argc+=1

if %argc% neq 1 (
  echo.
  echo Usage: download-ggml-model.cmd model
  CALL :list_models
  goto :eof
)

set model=%1

for %%b in (%models%) do (
  if "%%b"=="%model%" (
    CALL :download_model
    goto :eof
  )
)

echo Invalid model: %model%
CALL :list_models
goto :eof

:download_model
echo Downloading ggml model %model%...

cd "%models_path%"

if exist "whisper.cpp\models" (
    cd whisper.cpp\models
) else if exist "models" (
    cd models
) else (
    mkdir models
    cd models
)

if exist "ggml-%model%.bin" (
  echo Model %model% already exists. Skipping download.
  goto :eof
)

REM Check if model contains `tdrz` and update the src accordingly
echo %model% | findstr /C:"tdrz" >nul
if %ERRORLEVEL% equ 0 (
    set "src=https://huggingface.co/akashmjn/tinydiarize-whisper.cpp/resolve/main"
) else (
    set "src=https://huggingface.co/ggerganov/whisper.cpp/resolve/main"
)

PowerShell -NoProfile -ExecutionPolicy Bypass -Command "Start-BitsTransfer -Source %src%/ggml-%model%.bin -Destination ggml-%model%.bin"

if %ERRORLEVEL% neq 0 (
  echo Failed to download ggml model %model%
  echo Please try again later or download the original Whisper model files and convert them yourself.
  goto :eof
)

echo Done! Model %model% saved in %CD%\ggml-%model%.bin
echo You can now use it with the Whisper server.

goto :eof

:list_models
  echo.
  echo Available models:
  (for %%a in (%models%) do (
    echo %%a
  ))
  echo.
  goto :eof
