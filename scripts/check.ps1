param(
    [switch]$SkipEngineTests,
    [switch]$SkipWarshipsTests
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:PYTHONPATH = "."

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [Parameter(Mandatory = $true)]
        [string]$Command
    )
    Write-Host $Label
    Invoke-Expression $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

Invoke-Checked -Label "Running Ruff lint..." -Command "uv run ruff check ."

Invoke-Checked -Label "Running Ruff format check..." -Command "uv run ruff format --check ."

Invoke-Checked -Label "Running mypy..." -Command "uv run mypy"

if (-not $SkipEngineTests) {
    Invoke-Checked -Label "Running engine tests with coverage gate..." -Command "uv run pytest tests/engine --cov=engine --cov-report=term-missing --cov-fail-under=75"
}

if (-not $SkipWarshipsTests) {
    Invoke-Checked -Label "Running warships tests with coverage gate..." -Command "uv run pytest tests/warships --cov=warships.game --cov-report=term-missing --cov-fail-under=75"

    Invoke-Checked -Label "Running warships critical coverage gate..." -Command "uv run pytest tests/warships/unit/core tests/warships/unit/presets tests/warships/unit/app/services --cov=warships.game.core --cov=warships.game.presets --cov=warships.game.app.services --cov-report=term-missing --cov-fail-under=90"
}

Write-Host "All selected checks passed."
