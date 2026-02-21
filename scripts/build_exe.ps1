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
$envEngine = '.env.engine'
$envApp = '.env.app'

if (-not (Test-Path $glfwDll)) {
    throw "Required GLFW DLL not found: $glfwDll"
}
if (-not (Test-Path $envEngine)) {
    throw "Required env file not found: $envEngine"
}
if (-not (Test-Path $envApp)) {
    throw "Required env file not found: $envApp"
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
Copy-Item -Path $envEngine -Destination (Join-Path $distConfigDir ".env.engine") -Force
Copy-Item -Path $envApp -Destination (Join-Path $distConfigDir ".env.app") -Force

Write-Host "Build complete: dist\\$name\\$name.exe"
