# Requires: Python 3.11+ with PyInstaller installed
# Usage: run from project root or this script's folder in PowerShell
#   pwsh -f tools/build_exe.ps1 -Version 1.0.0

param(
    [string]$Version = "1.0.1"
)

$ErrorActionPreference = 'Stop'

# Go to project root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $scriptDir '..')
Set-Location $root

# Ensure output folder
$binDir = Join-Path $root 'bin'
if (!(Test-Path $binDir)) { New-Item -ItemType Directory -Path $binDir | Out-Null }

# Build temp work dir
$distDir = Join-Path $binDir 'dist'
$buildDir = Join-Path $binDir 'build'
if (Test-Path $distDir) { Remove-Item -Recurse -Force $distDir }
if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }

# Compute data folders to include
function Add-DataArg([string]$src, [string]$dst) {
    if (Test-Path $src) {
        return "--add-data=`"$src;$dst`""
    } else { return $null }
}

$dataArgs = @()
$assetsArg = Add-DataArg (Join-Path $root 'assets') 'assets'
$databaseArg = Add-DataArg (Join-Path $root 'database') 'database'
$docsArg = Add-DataArg (Join-Path $root 'docs') 'docs'
$extraArg = Add-DataArg (Join-Path $root 'GUI') 'GUI'
foreach ($a in @($assetsArg,$databaseArg,$docsArg,$extraArg)) { if ($a) { $dataArgs += $a } }

# Windows no-console build, one-folder layout
$iconPath = Join-Path $root 'assets\app.ico'
$iconOpt = $(if (Test-Path $iconPath) { "--icon=`"$iconPath`"" } else { '' })

$pyExe = (Get-Command python).Source


$argsList = @(
    '-m', 'PyInstaller',
    '--noconfirm',
    '--clean',
    '--onedir',
    '--windowed',
    $iconOpt,
    '--name', 'PracticeApp',
    '--workpath', $buildDir,
    '--distpath', $distDir,
    '--hidden-import', 'PyQt6',
    '--hidden-import', 'PyQt6.QtCore',
    '--hidden-import', 'PyQt6.QtGui',
    '--hidden-import', 'PyQt6.QtWidgets',
    '--hidden-import', 'jsonschema',
    '--hidden-import', 'jsonschema.validators',
    '--hidden-import', 'jsonschema.exceptions',
    # Collect all PyQt6 submodules, data, and binaries (Qt plugins)
    '--collect-submodules', 'PyQt6',
    '--collect-data', 'PyQt6',
    '--collect-binaries', 'PyQt6'
) | Where-Object { $_ -and $_ -ne '' }

if ($dataArgs -and $dataArgs.Count -gt 0) { $argsList += $dataArgs }

$argsList += 'main.py'

Write-Host "Running: python $($argsList -join ' ')" -ForegroundColor Cyan
& $pyExe $argsList

if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE" }

# Stamp version
$target = Join-Path $distDir 'PracticeApp'
if (Test-Path $target) {
    Set-Content -Path (Join-Path $target 'VERSION.txt') -Value $Version -Encoding UTF8
}

Write-Host "Build done. Dist at: $target" -ForegroundColor Green
