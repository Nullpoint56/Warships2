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

if (-not (Test-Path $glfwDll)) {
    throw "Required GLFW DLL not found: $glfwDll"
}

$args = @(
    '--noconfirm',
    '--clean',
    '--onedir',
    $windowFlag,
    '--name', $name,
    '--collect-all', 'pygfx',
    '--collect-all', 'wgpu',
    '--collect-all', 'rendercanvas',
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

Write-Host "Build complete: dist\\$name\\$name.exe"
