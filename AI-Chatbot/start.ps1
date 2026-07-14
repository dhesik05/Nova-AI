param(
  [string]$ProjectRoot = $(Split-Path -Parent $MyInvocation.MyCommand.Path)
)

$ErrorActionPreference = "Stop"

$venvDir = Join-Path $ProjectRoot ".venv"
$backendDir = Join-Path $ProjectRoot "backend"
$uploadDir = Join-Path $backendDir "uploads"
$vectorDir = Join-Path $backendDir "vector_store"

function Ensure-Dir($path) {
  if (!(Test-Path $path)) {
    New-Item -ItemType Directory -Path $path | Out-Null
  }
}

Write-Host "== D-AI startup (PowerShell) =="
Write-Host "ProjectRoot: $ProjectRoot"

# Create venv if missing
if (!(Test-Path $venvDir)) {
  Write-Host "Creating virtual environment at $venvDir ..."
  & python -m venv $venvDir
}

# Activate venv
$activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
if (!(Test-Path $activateScript)) {
  throw "Could not find venv activation script: $activateScript"
}
Write-Host "Activating venv..."
& $activateScript

# Upgrade tooling
Write-Host "Upgrading pip/setuptools/wheel..."
& python -m pip install --upgrade pip setuptools wheel

# Install deps
$reqFile = Join-Path $backendDir "requirements.txt"
Write-Host "Installing dependencies from $reqFile ..."
& python -m pip install -r $reqFile

# Ensure folders
Ensure-Dir $uploadDir
Ensure-Dir $vectorDir

# Start server (avoid pre-importing app here; uvicorn will import it once)
# This prevents startup hangs during endpoint verification.
Set-Location $backendDir

# Start server
$port = 8000
Write-Host "Starting FastAPI..."

# Use venv python explicitly (PowerShell PATH can be unreliable after activation)
$pythonExe = Join-Path $venvDir "Scripts\python.exe"

if (!(Test-Path $pythonExe)) {
  throw "Python executable not found: $pythonExe"
}
Write-Host "Using python: $pythonExe"

# Invoke via explicit command string to avoid PowerShell array/quoting issues
& "$pythonExe" -m uvicorn app.main:app --host "127.0.0.1" --port $port

Write-Host "== Server started: http://127.0.0.1:$port =="
