@echo off
chcp 65001 > nul
echo [DEBUG MODE] Batch script started.
echo.

REM Move to this directory
cd /d "%~dp0"
echo Current directory: %cd%
echo.

REM Check Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    goto END
)

REM Check/Create venv
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        goto END
    )
)

REM Activate venv
echo [INFO] Activating venv...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate venv.
    goto END
)

REM Install dependencies
if exist requirements.txt (
    echo [INFO] Installing requirements...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install requirements.
        goto END
    )
) else (
    echo [WARN] No requirements.txt found, skipping.
)

REM Run script
echo [INFO] Starting status.py...
python -u status.py
if errorlevel 1 (
    echo [ERROR] status.py failed or crashed.
    goto END
)

echo [SUCCESS] Script completed successfully.

:END
echo.
echo Press any key to exit...
pause >nul
