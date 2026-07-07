# Однократная настройка фронтенда для локальной разработки
Copy-Item "$PSScriptRoot\js\config.example.js" "$PSScriptRoot\js\config.js" -Force
Write-Host "Готово: js/config.js -> http://localhost:8000"
Write-Host "Запуск сайта: .\start.ps1"
