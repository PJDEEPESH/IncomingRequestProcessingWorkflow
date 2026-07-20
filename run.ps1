# One-click launcher: opens the backend (FastAPI) and frontend (Vite) in two windows.
# Usage:  right-click > Run with PowerShell   (or)   ./run.ps1
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting backend (FastAPI) on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList '-NoExit', '-Command', "cd `"$here`"; .\.venv\Scripts\python.exe -m uvicorn api:app --port 8000"

Start-Sleep -Seconds 2

Write-Host "Starting frontend (Vite) on http://localhost:5173 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList '-NoExit', '-Command', "cd `"$here\frontend`"; npm run dev"

Start-Sleep -Seconds 4
Write-Host "Opening the app in your browser..." -ForegroundColor Green
Start-Process "http://localhost:5173"
