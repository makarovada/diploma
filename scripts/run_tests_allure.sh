#!/usr/bin/env bash
# Запуск pytest с записью результатов для Allure и открытие отчёта в браузере.
# Требуется: pip install -e ".[dev]" и Allure CLI в PATH (https://github.com/allure-framework/allure2/releases).
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

if ! command -v allure >/dev/null 2>&1; then
  echo "Команда 'allure' не найдена. Установите Allure Commandline и добавьте его в PATH." >&2
  exit 1
fi

python -m pytest tests/ --alluredir=allure-results --clean-alluredir "$@"
pytest_status=$?
if [ "$pytest_status" -ne 0 ]; then
  echo "pytest завершился с кодом $pytest_status; отчёт Allure всё равно будет сгенерирован по собранным результатам."
fi

allure serve allure-results
