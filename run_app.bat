@echo off
setlocal
cd /d "%~dp0"

REM ===== Timestamp for backups =====
set TIMESTAMP=%DATE:~10,4%-%DATE:~4,2%-%DATE:~7,2%_%TIME:~0,2%-%TIME:~3,2%-%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

REM ===== Ensure backups folder exists and copy DB =====
if not exist backups mkdir backups
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

REM ===== Start the Streamlit app in a separate window so this script can continue =====
start "" venv\Scripts\python.exe -m streamlit run "%~dp0Phone_Shop_SQLite_System.py"

REM ===== Git auto-push every hour =====
REM NOTE: embedding a PAT in a script is insecure. Consider using an environment variable or Windows Credential Manager instead.
set GIT_TOKEN=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
set REPO_URL=https://%GIT_TOKEN%@github.com/mohamedelcaptin/elcaptin_system.git

REM Check for git
git --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo Git is NOT installed or not in PATH. Auto-push will be skipped.
  goto :no_git_wait
)

REM Determine the current branch (fallback to main if detection fails)
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set GIT_BRANCH=%%b
if "%GIT_BRANCH%"=="" set GIT_BRANCH=main

:push_loop
echo [%DATE% %TIME%] Preparing git add/commit/push...

REM Add all changes (including backups)
git add -A

REM Create a timestamped commit message
for /f "delims=" %%c in ('powershell -NoProfile -Command "Get-Date -Format ''yyyy-MM-dd_HH-mm-ss''"') do set NOW=%%c

REM Commit if there are changes; ignore if nothing to commit
git commit -m "Auto backup %NOW%" >nul 2>&1 || echo No changes to commit.

REM Push to the repository using the token in the URL (push current branch)
git push %REPO_URL% %GIT_BRANCH% >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo [%DATE% %TIME%] Push failed. Check network/credentials.
) else (
  echo [%DATE% %TIME%] Push succeeded.
)

REM Wait one hour (3600 seconds) then loop again
timeout /t 3600 /nobreak >nul
goto push_loop

:no_git_wait
REM If git is not available, keep the script alive and retry periodically if you like.
:wait_loop
timeout /t 3600 /nobreak >nul
goto wait_loop

endlocal
pause