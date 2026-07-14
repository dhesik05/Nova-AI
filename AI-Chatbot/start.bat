@echo off
setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

set "VENV_DIR=%PROJECT_ROOT%\.venv"
set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "UPLOAD_DIR=%BACKEND_DIR%\uploads"
set "VECTOR_DIR=%BACKEND_DIR%\vector_store"
set "REQ_FILE=%BACKEND_DIR%\requirements.txt"

echo == D-AI startup (BAT) ==
echo ProjectRoot: %PROJECT_ROOT%

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo Creating virtual environment at %VENV_DIR% ...
  python -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"

echo Upgrading pip/setuptools/wheel...
python -m pip install --upgrade pip setuptools wheel

echo Installing dependencies from "%REQ_FILE%" ...
python -m pip install -r "%REQ_FILE%"

if not exist "%UPLOAD_DIR%" mkdir "%UPLOAD_DIR%"
if not exist "%VECTOR_DIR%" mkdir "%VECTOR_DIR%"

echo Initializing database...
python -c "import backend.app.main as m; print('DB init ok')"

echo Starting FastAPI...
set "PORT=8000"
uvicorn backend.app.main:app --host 127.0.0.1 --port %PORT%

echo == Server started: http://127.0.0.1:%PORT% ==
