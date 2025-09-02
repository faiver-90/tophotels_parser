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
echo Step 6: Run to google drive
echo =============================
if exist "%cd%\run_to_google_drive.py" (
  python "run_to_google_drive.py"
  if errorlevel 1 (
    echo [!] Script exited with errors.
    goto :PAUSE_AND_EXIT_ERR
  )
) else (
  echo [!] run_to_google_drive.py not found in "%cd%".
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