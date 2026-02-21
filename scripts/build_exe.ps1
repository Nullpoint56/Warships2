param(
    [switch]$DebugConsole
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$entry = 'warships\main.py'
$name = if ($DebugConsole) { 'WarshipsDbg' } else { 'Warships' }
$windowFlag = if ($DebugConsole) { '--console' } else { '--windowed' }
$glfwDll = '.venv\Lib\site-packages\glfw\glfw3.dll'
$envEngineTemplate = '.env.engine.example'
$envAppTemplate = '.env.app.example'

function New-EnvFromTemplate {
    param(
        [Parameter(Mandatory = $true)][string]$TemplatePath,
        [Parameter(Mandatory = $true)][string]$DestinationPath,
        [Parameter(Mandatory = $true)][hashtable]$Overrides
    )

    if (-not (Test-Path $TemplatePath)) {
        throw "Required env template not found: $TemplatePath"
    }

    $lines = Get-Content -Path $TemplatePath
    $seen = @{}
    $output = New-Object System.Collections.Generic.List[string]

    foreach ($line in $lines) {
        if ($line -match '^\s*([A-Z0-9_]+)\s*=.*$') {
            $key = $Matches[1]
            if ($Overrides.ContainsKey($key)) {
                $value = [string]$Overrides[$key]
                $output.Add("$key=$value")
                $seen[$key] = $true
                continue
            }
        }
        $output.Add($line)
    }

    foreach ($key in $Overrides.Keys) {
        if (-not $seen.ContainsKey($key)) {
            $value = [string]$Overrides[$key]
            $output.Add("$key=$value")
        }
    }

    Set-Content -Path $DestinationPath -Value $output -Encoding UTF8
}

if (-not (Test-Path $glfwDll)) {
    throw "Required GLFW DLL not found: $glfwDll"
}

$args = @(
    '--noconfirm',
    '--clean',
    '--onedir',
    $windowFlag,
    '--name', $name,
    '--collect-all', 'wgpu',
    '--collect-all', 'rendercanvas',
    '--collect-all', 'uharfbuzz',
    '--collect-all', 'freetype',
    '--add-binary', "$glfwDll;.",
    $entry
)

Write-Host "Building $name..."
$pyinstallerExe = '.venv\Scripts\pyinstaller.exe'
$venvPython = '.venv\Scripts\python.exe'

if (Test-Path $pyinstallerExe) {
    & $pyinstallerExe @args
} elseif (Test-Path $venvPython) {
    & $venvPython -m PyInstaller @args
} else {
    py -m PyInstaller @args
}

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$distConfigDir = Join-Path -Path "dist\\$name" -ChildPath "appdata\\config"
New-Item -ItemType Directory -Path $distConfigDir -Force | Out-Null

$engineProduction = @{
    ENGINE_RUNTIME_PROFILE = 'release-like'
    ENGINE_LOG_LEVEL = 'WARNING'
    ENGINE_METRICS_ENABLED = '0'
    ENGINE_UI_OVERLAY_ENABLED = '0'
    ENGINE_PROFILING_ENABLED = '0'
    ENGINE_INPUT_TRACE_ENABLED = '0'
    ENGINE_DIAGNOSTICS_ENABLED = '0'
    ENGINE_DIAGNOSTICS_CRASH_ENABLED = '1'
    ENGINE_DIAGNOSTICS_CRASH_DIR = 'appdata/crash'
    ENGINE_DIAGNOSTICS_PROFILING_MODE = 'off'
    ENGINE_DIAGNOSTICS_REPLAY_ENABLED = '0'
    ENGINE_DIAGNOSTICS_RENDER_STAGE_EVENTS_ENABLED = '0'
    ENGINE_DIAGNOSTICS_HTTP_ENABLED = '0'
    ENGINE_RENDER_VSYNC = '1'
    ENGINE_RENDER_LOOP_MODE='continuous'
}

$appProduction = @{
    WARSHIPS_DEBUG_INPUT = '0'
    WARSHIPS_DEBUG_UI = '0'
    WARSHIPS_LOG_LEVEL = 'WARNING'
    LOG_FORMAT = 'json'
}

New-EnvFromTemplate `
    -TemplatePath $envEngineTemplate `
    -DestinationPath (Join-Path $distConfigDir ".env.engine") `
    -Overrides $engineProduction
New-EnvFromTemplate `
    -TemplatePath $envAppTemplate `
    -DestinationPath (Join-Path $distConfigDir ".env.app") `
    -Overrides $appProduction

Write-Host "Build complete: dist\\$name\\$name.exe"
