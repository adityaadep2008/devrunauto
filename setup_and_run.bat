@echo off
REM Setup and Run Script for DroidRun Commerce Agent
REM Enforces Python 3.10, checks ADB, and installs dependencies.

set VENV_DIR=venv

echo ===================================================
echo      DroidRun Commerce Agent - Setup & Run
echo ===================================================

echo.
echo [Step 1] Checking for ADB Device...
adb devices
adb devices | findstr "device$" >nul
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] No ADB device connected! 
    echo Please connect your Android device/emulator and enable USB Debugging.
    echo If using an emulator, ensure it is running.
    pause
    exit /b
)
echo [OK] Device connected.

echo.
echo [Step 2] Checking Python Environment...
if exist "%VENV_DIR%\Scripts\python.exe" (
    echo [OK] Found existing venv. Using it.
    set PYTHON_CMD="%VENV_DIR%\Scripts\python.exe"
    goto :INSTALL_DEPS
)

echo [INFO] No venv found. Checks for Python 3.10...
py -3.10 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.10 is required but not found via 'py -3.10'.
    echo Please install Python 3.10 from python.org.
    pause
    exit /b
)

echo [INFO] Creating venv...
py -3.10 -m venv %VENV_DIR%
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create venv.
    pause
    exit /b
)
set PYTHON_CMD="%VENV_DIR%\Scripts\python.exe"

:INSTALL_DEPS
echo.
echo [Step 3] Installing Dependencies (DroidRun)...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install -r requirements.txt

echo.
echo [Step 4] Checking Configuration...
if not exist ".env" (
    echo [WARNING] .env file not found!
    if exist ".env.example" (
        copy .env.example .env
        echo [INFO] Created .env from .env.example. Please add your API Keys now.
        notepad .env
    )
    pause
)

echo.
echo [Step 5] DroidRun Portal Setup
echo If this is your first time, you may need to setup the DroidRun Portal on the device.
echo Ensure 'droidrun' is initialized if required by the framework.
echo.

echo ===================================================
echo      Ready to Start Commerce Agent
echo ===================================================
echo Usage: commerce_agent.py --task [shopping|food] --query "Item"
echo.
echo Example: Running Shopping Search for "iPhone 15"...
echo.
%PYTHON_CMD% commerce_agent.py --task shopping --query "iPhone 15"

pause
