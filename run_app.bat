@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ===== Timestamp for backups =====
for /f "tokens=1-3 delims=/ " %%a in ("%date%") do (
  set "MM=%%a" & set "DD=%%b" & set "YYYY=%%c"
)
for /f "tokens=1-3 delims=:. " %%a in ("%time%") do (
  set "HH=%%a" & set "Min=%%b" & set "Sec=%%c"
)
if "%HH:~0,1%"==" " set "HH=0%HH:~1,1%"
set "TIMESTAMP=%YYYY%-%MM%-%DD%_%HH%-%Min%-%Sec%"

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

REM ===== Start the Streamlit app (separate window) =====
start "" venv\Scripts\python.exe -m streamlit run "%~dp0Phone_Shop_SQLite_System.py"

REM ===== Check for git =====
git --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
  echo Git is NOT installed or not in PATH. Auto-push will be skipped.
  goto :no_git_wait
)

REM ===== Determine branch, fallback to main =====
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set "GIT_BRANCH=%%b"
if "%GIT_BRANCH%"=="" set "GIT_BRANCH=main"

REM ===== Decide where to push: use %REPO_URL% if set else use "origin" =====
if defined REPO_URL (
  echo REPO_URL is set: %REPO_URL%
  set "GIT_PUSH_TARGET=%REPO_URL%"
) else (
  echo REPO_URL not set; using remote name "origin"
  set "GIT_PUSH_TARGET=origin"
)

:push_loop
echo [%date% %time%] Preparing git add/commit/push...

REM Add all changes (including backups) - consider adding backups/ to .gitignore if you don't want them pushed
git add -A

REM Create a timestamped commit message
for /f "delims=" %%c in ('powershell -NoProfile -Command "Get-Date -Format ''yyyy-MM-dd_HH-mm-ss''"') do set "NOW=%%c"

REM Commit if there are changes; capture commit output
git commit -m "Auto backup %NOW%" >git_commit_output.txt 2>&1
set "GIT_COMMIT_EXIT=%ERRORLEVEL%"
type git_commit_output.txt

if %GIT_COMMIT_EXIT% neq 0 (
  echo No changes to commit or commit failed. (exit %GIT_COMMIT_EXIT%)
) else (
  echo Commit created.
)

REM Push to the repository; write full output to file for debugging
echo Pushing to: %GIT_PUSH_TARGET% %GIT_BRANCH%
git push %GIT_PUSH_TARGET% %GIT_BRANCH% >git_push_output.txt 2>&1
set "GIT_PUSH_EXIT=%ERRORLEVEL%"

echo --- git push output follows ---
type git_push_output.txt
echo --- end git push output ---

if %GIT_PUSH_EXIT% neq 0 (
  echo [%date% %time%] Push failed (exit %GIT_PUSH_EXIT%). See git_push_output.txt for details.
  echo Common fixes:
  echo  - Ensure REPO_URL is correct or change to 'origin'
  echo  - Run: git remote -v
  echo  - Configure credentials: git config --global credential.helper manager-core (Windows)
  echo  - If you intend to use a PAT in the remote URL, set REPO_URL to the full https://...git form or add origin with that URL
) else (
  echo [%date% %time%] Push succeeded.
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