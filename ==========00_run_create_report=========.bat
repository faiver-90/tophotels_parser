chcp 65001 >nul
@echo off
setlocal
cd /d "%~dp0"

echo =============================
echo Checking for Python...
echo =============================

REM Try to find Python
set "PYTHON="
py -c "import sys; print(sys.executable)" >nul 2>nul
if not errorlevel 1 (
    echo Python found via 'py'
    set "PYTHON=py"
)

if not defined PYTHON (
    python --version >nul 2>nul
    if not errorlevel 1 (
        echo Python found via 'python'
        set "PYTHON=python"
    )
)

if not defined PYTHON (
    python3 --version >nul 2>nul
    if not errorlevel 1 (
        echo Python found via 'python3'
        set "PYTHON=python3"
    )
)

if not defined PYTHON (
    echo Python not found. Downloading installer...

    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.6/python-3.11.6-amd64.exe' -OutFile 'python_installer.exe'"
    if not exist "python_installer.exe" (
        echo Failed to download Python installer.
        pause
        exit /b
    )

    REM Silent install for all users; default path is %ProgramFiles%\Python311\
    start /wait "" python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del /q "python_installer.exe"

    REM Use absolute path to freshly installed python to avoid PATH refresh issues
    if exist "%ProgramFiles%\Python311\python.exe" (
        set "PYTHON=%ProgramFiles%\Python311\python.exe"
        echo Python installed at: %PYTHON%
    ) else (
        REM Fallback to user install location just in case
        if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
            set "PYTHON=%LocalAppData%\Programs\Python\Python311\python.exe"
            echo Python installed at: %PYTHON%
        ) else (
            echo Python installation failed. Aborting.
            pause
            exit /b
        )
    )
)

echo.
echo Using Python: %PYTHON%

REM === Create venv ===
if not exist ".venv" (
    echo Creating virtual environment...
    "%PYTHON%" -m venv ".venv"
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b
    )
)

REM === Activate venv ===
echo Activating virtual environment...
call ".venv\Scripts\activate.bat"

REM === Upgrade pip and install deps ===
if exist "requirements.txt" (
    echo Installing dependencies from requirements.txt...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    if errorlevel 1 (
        echo Failed to upgrade pip.
        pause
        exit /b
    )
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b
    )
) else (
    echo requirements.txt not found. Skipping deps installation.
)

REM === Run your script ===
echo =============================
echo Running: run_create_report.py
echo =============================
".venv\Scripts\python.exe" "run_create_report.py"
if errorlevel 1 (
    echo Script exited with errors.
    pause
    exit /b
)

echo.
echo All done.
echo Press any key to exit...
pause >nul
exit /b
