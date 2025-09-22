# Requires: WiX Toolset v3.11 installed and added to PATH (candle.exe, light.exe, heat.exe)
# Usage: pwsh -f update/installer/build_installer.ps1 -Version 1.0.0 -DistDir bin/dist/PracticeApp

param(
  [string]$Version = "1.0.0",
  [string]$DistDir = "bin/dist/PracticeApp"
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $scriptDir '../..')
Set-Location $root

# Verify dist dir
$dist = Resolve-Path $DistDir
if (!(Test-Path $dist)) { throw "Dist not found: $dist" }

function Resolve-WixTool([string] $name) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $pf = $env:ProgramFiles
  $pf86 = ${env:ProgramFiles(x86)}
  $candidates = @(
    "$pf86\WiX Toolset v3.11\bin\$name.exe",
    "$pf\WiX Toolset v3.11\bin\$name.exe",
    "$pf86\WiX Toolset v3.14\bin\$name.exe",
    "$pf\WiX Toolset v3.14\bin\$name.exe"
  ) | Where-Object { $_ -and (Test-Path $_) }
  foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
  throw "Cannot find WiX tool '$name'. Please install WiX Toolset v3.x and ensure $name.exe is in PATH or installed under Program Files."
}

$heatExe = Resolve-WixTool 'heat'
$candleExe = Resolve-WixTool 'candle'
$lightExe = Resolve-WixTool 'light'

# Harvest files into a WiX fragment
$wxsDir = Join-Path $scriptDir 'wix'
if (!(Test-Path $wxsDir)) { New-Item -ItemType Directory -Path $wxsDir | Out-Null }
$heatWxs = Join-Path $wxsDir 'Files.wxs'

$heatArgs = @('dir', "$dist", '-cg', 'AppFiles', '-dr', 'INSTALLDIR', '-sreg', '-srd', '-gg', '-g1', '-sf', '-scom', '-sfrag', '-var', 'var.DistDir', '-out', "$heatWxs")
Write-Host ("Running: $heatExe " + ($heatArgs -join ' ')) -ForegroundColor Cyan
& $heatExe $heatArgs

# Compile
$license = Join-Path $scriptDir 'LICENSE.rtf'
$candleArgs = @(
  '-dDistDir=' + $dist,
  '-dLicenseRtf=' + $license,
  (Join-Path $scriptDir 'Product.wxs'),
  $heatWxs
)
Write-Host ("Running: $candleExe " + ($candleArgs -join ' ')) -ForegroundColor Cyan
& $candleExe $candleArgs

# Link
$msiName = "PracticeApp-$Version.msi"
$lightArgs = @(
  '-ext', 'WixUIExtension',
  '-ext', 'WixUtilExtension',
  '-cultures:zh-CN',
  '-o', (Join-Path $scriptDir $msiName),
  (Join-Path $wxsDir 'Files.wixobj'),
  (Join-Path $scriptDir 'Product.wixobj')
)
Write-Host ("Running: $lightExe " + ($lightArgs -join ' ')) -ForegroundColor Cyan
& $lightExe $lightArgs

if ($LASTEXITCODE -ne 0) { throw "WiX linking failed: $LASTEXITCODE" }

Write-Host "MSI generated: $(Join-Path $scriptDir $msiName)" -ForegroundColor Green
