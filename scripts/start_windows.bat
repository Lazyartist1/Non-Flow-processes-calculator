@echo off
REM start_windows.bat - create venv if missing, install requirements, and run the development server

echo Starting helper: start_windows.bat

IF NOT EXIST ".venv\Scripts\python.exe" (
  echo Creating virtual environment .venv
  python -m venv .venv
) ELSE (
  echo Virtual environment found
)

echo Upgrading pip and installing requirements
.venv\Scripts\python -m pip install --upgrade pip setuptools wheel
.venv\Scripts\python -m pip install -r requirements.txt

echo Running API (press Ctrl+C in this window to stop)
.venv\Scripts\python api.py
pause
