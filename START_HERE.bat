@echo off
setlocal enabledelayedexpansion
echo ===========================================
echo OUMI AGENT - SETUP AND STARTUP (v2.4)
echo ===========================================
echo.

:: 1. Detect Python
set PYTHON_CMD=python
python --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [Info] 'python' not found, trying 'py' launcher...
    py --version >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        set PYTHON_CMD=py
    ) else (
        echo ERROR: Python is not found. Please install Python from python.org!
        pause
        exit /b
    )
)

echo [STEP 1/2] Installing Library Speed Boosts...
echo (Enabling NVIDIA GPU acceleration for your RTX 4050...)
%PYTHON_CMD% -m pip install flask flask-cors python-dotenv openai bitsandbytes accelerate transformers sentencepiece
%PYTHON_CMD% -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install GPU libraries.
    pause
    exit /b
)

echo [STEP 2/2] Starting the AI Brain...
%PYTHON_CMD% server_v2.py
if %ERRORLEVEL% NEQ 0 (
    echo SERVER CRASHED! 
)

pause
