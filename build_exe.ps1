$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Ambiente virtual não encontrado em .venv. Crie-o antes de gerar o executável."
}

& $python -m pip install -e ".[build]"
& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name postgres-rpg `
    --add-data "sql;sql" `
    --paths src `
    src\rpg\__main__.py

Write-Host "Executável criado em dist\postgres-rpg.exe"