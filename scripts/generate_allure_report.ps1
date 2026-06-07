# Генерация статического HTML-отчёта Allure без запуска тестов.
# Требуется: Allure CLI в PATH и каталог allure-results (см. docs/testing.md).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$allure = Get-Command allure -ErrorAction SilentlyContinue
if (-not $allure) {
    Write-Error "Команда 'allure' не найдена. Установите Allure Commandline и добавьте его в PATH."
}

if (-not (Test-Path "allure-results")) {
    Write-Error "Каталог allure-results не найден. Сначала выполните: python -m pytest tests/ --alluredir=allure-results --clean-alluredir"
}

allure generate allure-results --clean -o allure-report
Write-Host "Отчёт: $root\allure-report\index.html"
