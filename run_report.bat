@echo off
setlocal
cd /d "%~dp0"

echo =============================
echo 🔍 Checking for Python...
echo =============================

REM Try to find Python
set PYTHON=
py -c "import sys; print(sys.executable)" >nul 2>nul
if not errorlevel 1 (
    echo ✅ Python found via 'py'
    set PYTHON=py
)

if not defined PYTHON (
    python --version >nul 2>nul
    if not errorlevel 1 (
        echo ✅ Python found via 'python'
        set PYTHON=python
    )
)

if not defined PYTHON (
    python3 --version >nul 2>nul
    if not errorlevel 1 (
        echo ✅ Python found via 'python3'
        set PYTHON=python3
    )
)

if not defined PYTHON (
    echo ❌ Python not found. Downloading installer...
    powershell -Command "Start-Process 'https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe' -ArgumentList '/quiet InstallAllUsers=1 PrependPath=1 Include_test=0' -Wait"

    python --version >nul 2>nul
    if not errorlevel 1 (
        echo ✅ Python installed successfully.
        set PYTHON=python
    ) else (
        echo ❌ Python installation failed. Aborting.
        pause
        exit /b
    )
)

echo.
echo 🐍 Using Python: %PYTHON%

REM === Create or activate virtual environment ===
if not exist ".venv" (
    echo 🔧 Creating virtual environment...
    %PYTHON% -m venv .venv
)

REM Use pip from venv
echo 🔄 Activating virtual environment...
call ".venv\Scripts\activate.bat"

REM === Install dependencies ===
if exist requirements.txt (
    echo 📦 Installing dependencies from requirements.txt...
    .venv\Scripts\pip.exe install --upgrade pip
    .venv\Scripts\pip.exe install -r requirements.txt
)

REM === Run scripts ===
echo =============================
echo ▶ Running: parce_screenshots.py
echo =============================
.venv\Scripts\python.exe parce_screenshots.py

echo =============================
echo ▶ Running: move_shot_to_word.py
echo =============================
.venv\Scripts\python.exe move_shot_to_word.py

echo.
echo ✅ All scripts completed.
echo Press any key to exit...
pause >nul
exit /b
