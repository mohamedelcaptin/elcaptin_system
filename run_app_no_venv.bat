@echo off
cd /d "%~dp0"
python -m pip install --upgrade pip
pip install streamlit pandas >nul
streamlit run "%~dp0Phone_Shop_SQLite_System.py"
pause
