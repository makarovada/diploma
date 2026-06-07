# Headless-прогон Locust против запущенного DataNorma API.
# Требуется: pip install -e ".[load]" и сервер на LOAD_TEST_HOST (по умолчанию http://127.0.0.1:8080).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$hostUrl = if ($env:LOAD_TEST_HOST) { $env:LOAD_TEST_HOST } else { "http://127.0.0.1:8080" }
$users = if ($env:LOAD_TEST_USERS) { $env:LOAD_TEST_USERS } else { "10" }
$spawnRate = if ($env:LOAD_TEST_SPAWN_RATE) { $env:LOAD_TEST_SPAWN_RATE } else { "2" }
$runTime = if ($env:LOAD_TEST_DURATION) { $env:LOAD_TEST_DURATION } else { "1m" }
$outDir = if ($env:LOAD_TEST_OUT_DIR) { $env:LOAD_TEST_OUT_DIR } else { "loadtest-results" }

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host "Locust: host=$hostUrl users=$users spawn_rate=$spawnRate duration=$runTime"

locust `
  -f loadtests/locustfile.py `
  --host $hostUrl `
  --headless `
  -u $users `
  -r $spawnRate `
  -t $runTime `
  --html "$outDir/report.html" `
  --csv "$outDir/stats" `
  @args

if ($LASTEXITCODE -ne 0) {
    Write-Error "Locust завершился с кодом $LASTEXITCODE"
}

Write-Host "Отчёт: $root\$outDir\report.html"
