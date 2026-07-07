# Локальный сервер для сайта (порт 3000)
Set-Location $PSScriptRoot
if (-not (Test-Path "js\config.js")) {
    & "$PSScriptRoot\setup-local.ps1"
}
Write-Host "Сайт: http://localhost:3000"
npx --yes serve . -l 3000
