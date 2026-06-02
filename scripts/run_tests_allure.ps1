# Запуск pytest с записью результатов для Allure и открытие отчёта в браузере.
# Требуется: pip install -e ".[dev]" и Allure CLI в PATH (https://github.com/allure-framework/allure2/releases).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$allure = Get-Command allure -ErrorAction SilentlyContinue
if (-not $allure) {
    Write-Error "Команда 'allure' не найдена. Установите Allure Commandline и добавьте его в PATH."
}

python -m pytest tests/ --alluredir=allure-results --clean-alluredir @args
if ($LASTEXITCODE -ne 0) {
    Write-Host "pytest завершился с кодом $LASTEXITCODE; отчёт Allure всё равно будет сгенерирован по собранным результатам."
}

allure serve allure-results
