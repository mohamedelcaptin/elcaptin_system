@echo off
setlocal
cd /d "%~dp0"

set TIMESTAMP=%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%_%TIME:~0,2%-%TIME:~3,2%-%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
copy "phone_shop.db" "backups\phone_shop_%TIMESTAMP%.db"
REM ===== Check Python =====
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo Python is NOT installed or not in PATH.
  echo Download from: https://www.python.org/downloads/
  pause
  exit /b 1
)

REM ===== Create venv if missing =====
if not exist venv\Scripts\python.exe (
  echo Creating virtual environment...
  python -m venv venv

  REM ===== Install required packages once =====
  echo Installing required packages...
  venv\Scripts\python.exe -m pip install --upgrade pip
  venv\Scripts\python.exe -m pip install streamlit pandas numpy openpyxl
)

REM ===== Run the Streamlit app =====
venv\Scripts\python.exe -m streamlit run "%~dp0Phone_Shop_SQLite_System.py"

pause
endlocal