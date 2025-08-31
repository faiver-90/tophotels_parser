@echo off
REM ==================================================================
REM  Unified script (ASCII-only):
REM    - chcp 65001 (optional UTF-8 in console)
REM    - Ensure PowerShell ExecutionPolicy (CurrentUser -> RemoteSigned)
REM    - Ensure Python present; install 3.12 x64 via winget if missing
REM    - Create and activate local .venv next to this file
REM    - pip install -r requirements.txt (if exists)
REM    - pip install/upgrade playwright and install browsers
REM    - Run run_create_report.py inside the venv
REM    - Keep window open at the end
REM ==================================================================

setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

REM 0) Go to script directory
cd /d "%~dp0"

echo =============================
echo Step 1: Execution Policy
echo =============================
for /f "usebackq delims=" %%E in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "try { (Get-ExecutionPolicy -Scope CurrentUser) } catch { 'Undefined' }"` ) do set "CURR_EP=%%E"
if /I not "%CURR_EP%"=="RemoteSigned" if /I not "%CURR_EP%"=="Bypass" (
  echo [*] Setting PowerShell ExecutionPolicy RemoteSigned for CurrentUser...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force"
) else (
  echo [*] ExecutionPolicy already: %CURR_EP%
)

echo.
echo =============================
echo Step 2: Python check/install
echo =============================
set "PY_EXE="
where py >nul 2>&1 && set "PY_EXE=py"
if not defined PY_EXE (
  where python >nul 2>&1 && set "PY_EXE=python"
)
if not defined PY_EXE (
  echo [*] Python not found. Trying to install Python 3.12 x64 via winget...
  winget --version >nul 2>&1 || (
    echo [!] winget is not available. Install Python 3.12 x64 manually and re-run.
    goto :PAUSE_AND_EXIT_ERR
  )
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo [!] winget failed to install Python. Install manually and re-run.
    goto :PAUSE_AND_EXIT_ERR
  )
  where py >nul 2>&1 && set "PY_EXE=py"
  if not defined PY_EXE (
    where python >nul 2>&1 && set "PY_EXE=python"
  )
  if not defined PY_EXE (
    echo [!] Python still not available in PATH. Add it and re-run.
    goto :PAUSE_AND_EXIT_ERR
  )
) else (
  echo [*] Python found: %PY_EXE%
)

echo.
echo =============================
echo Step 2.5: Git check/update
echo =============================
set "PS1=%~dp0bat_files\setup_git_and_update.ps1"
if not exist "%PS1%" (
  echo [!] Missing: %PS1%
  goto :PAUSE_AND_EXIT_ERR
)

REM можно добавить -PersistUserPath, чтобы путь к Git прописался в PATH пользователя
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -RepoPath "%cd%" -PersistUserPath
if errorlevel 1 (
  echo [!] Git setup/update failed.
  goto :PAUSE_AND_EXIT_ERR
)

echo.
echo =============================
echo Step 3: Create/activate .venv
echo =============================
set "VENV_DIR=%cd%\.venv"
if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [*] Creating venv at "%VENV_DIR%"
  "%PY_EXE%" -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [!] Failed to create venv.
    goto :PAUSE_AND_EXIT_ERR
  )
)
call "%VENV_DIR%\Scripts\activate.bat"
if errorlevel 1 (
  echo [!] Failed to activate venv.
  goto :PAUSE_AND_EXIT_ERR
)

echo.
echo =============================
echo Step 4: pip upgrade and deps
echo =============================
python -m pip install --upgrade pip
if errorlevel 1 echo [!] pip upgrade returned non-zero exit code.

if exist "%cd%\requirements.txt" (
  echo [*] Installing requirements.txt...
  python -m pip install -r "%cd%\requirements.txt"
  if errorlevel 1 (
    echo [!] Failed to install requirements.txt.
    goto :PAUSE_AND_EXIT_ERR
  )
) else (
  echo [*] No requirements.txt found. Skipping.
)

echo.
echo =============================
echo Step 5: Playwright install
echo =============================
python -m pip install --upgrade playwright
if errorlevel 1 (
  echo [!] Failed to install Playwright via pip.
  goto :PAUSE_AND_EXIT_ERR
)
python -m playwright install chromium
if errorlevel 1 (
  echo [!] Failed to install Playwright browsers.
  goto :PAUSE_AND_EXIT_ERR
)

echo.
echo =============================
echo Step 6: Run report
echo =============================
if exist "%cd%\run_create_report.py" (
  python "run_create_report.py"
  if errorlevel 1 (
    echo [!] Script exited with errors.
    goto :PAUSE_AND_EXIT_ERR
  )
) else (
  echo [!] run_create_report.py not found in "%cd%".
  goto :PAUSE_AND_EXIT_ERR
)

echo.
echo All done.
goto :PAUSE_AND_EXIT_OK

:PAUSE_AND_EXIT_ERR
echo.
echo Finished with errors. Press any key to exit...
pause >nul
exit /b 1

:PAUSE_AND_EXIT_OK
echo Press any key to exit...
pause >nul
exit /b 0
