param(
    [switch]$SkipEngineTests,
    [switch]$SkipWarshipsTests
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:PYTHONPATH = "."

Write-Host "Running Ruff lint..."
uv run ruff check .

Write-Host "Running Ruff format check..."
uv run ruff format --check .

Write-Host "Running mypy..."
uv run mypy

if (-not $SkipEngineTests) {
    Write-Host "Running engine tests with coverage gate..."
    uv run pytest tests/engine --cov=engine --cov-report=term-missing --cov-fail-under=75
}

if (-not $SkipWarshipsTests) {
    Write-Host "Running warships tests with coverage gate..."
    uv run pytest tests/warships --cov=warships.game --cov-report=term-missing --cov-fail-under=75

    Write-Host "Running warships critical coverage gate..."
    uv run pytest `
        tests/warships/unit/core `
        tests/warships/unit/presets `
        tests/warships/unit/app/services `
        --cov=warships.game.core `
        --cov=warships.game.presets `
        --cov=warships.game.app.services `
        --cov-report=term-missing `
        --cov-fail-under=90
}

Write-Host "All selected checks passed."
