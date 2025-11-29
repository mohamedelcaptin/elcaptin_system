@echo off
setlocal
cd /d "%~dp0"

REM -- log file
set LOGFILE=%~dp0run_log.txt
echo ===== Run started at %DATE% %TIME% > "%LOGFILE%"

REM -- ensure python available
python --version >> "%LOGFILE%" 2>&1
if ERRORLEVEL 1 (
  echo Python not found in PATH. >> "%LOGFILE%"
  echo Python not found in PATH. Please install Python or run from a prompt where `python` works.
  type "%LOGFILE%"
  pause
  exit /b 1
)

REM -- Create venv if missing
if not exist "venv\Scripts\python.exe" (
  echo Creating virtual environment... >> "%LOGFILE%"
  python -m venv venv >> "%LOGFILE%" 2>&1
  if ERRORLEVEL 1 (
    echo Failed to create venv. Check permissions. >> "%LOGFILE%"
    type "%LOGFILE%"
    pause
    exit /b 1
  )
)

REM -- Use venv python directly to avoid PATH issues
set VENV_PY=%~dp0venv\Scripts\python.exe

REM -- Upgrade pip
"%VENV_PY%" -m pip install --upgrade pip >> "%LOGFILE%" 2>&1

REM -- Install required packages (silent)
"%VENV_PY%" -m pip install streamlit pandas >> "%LOGFILE%" 2>&1

echo Running Streamlit with venv python... >> "%LOGFILE%"
"%VENV_PY%" -m streamlit run "%~dp0Phone_Shop_SQLite_System.py" >> "%LOGFILE%" 2>&1

echo ===== Run ended at %DATE% %TIME% >> "%LOGFILE%"
echo Logs written to: "%LOGFILE%"
type "%LOGFILE%"
pause
endlocal
