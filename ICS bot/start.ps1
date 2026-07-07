# Локальный запуск бэкенда (FastAPI + Telegram-бот)
Set-Location $PSScriptRoot
& "$PSScriptRoot\venv\Scripts\Activate.ps1"
Write-Host "API: http://localhost:8000/health"
uvicorn main:app --host 0.0.0.0 --port 8000
