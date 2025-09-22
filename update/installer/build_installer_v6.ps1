param(
  [string]$Version = '1.0.0',
  [string]$DistDir = 'bin/dist/PracticeApp',
  [string]$Culture = 'zh-CN'
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $scriptDir '../..')
Set-Location $root

if (-not (Get-Command wix -ErrorAction SilentlyContinue)) {
  Write-Error 'WiX v6 CLI (wix) not found. Install via Scoop: scoop install wixtoolset.'
  exit 1
}

$dist = (Resolve-Path $DistDir).Path
if (-not (Test-Path $dist)) {
  $msg = 'Dist not found: ' + $dist
  Write-Error $msg
  exit 1
}

$work = Join-Path $scriptDir 'wixv6'
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
New-Item -ItemType Directory -Path $work | Out-Null

$filesV3 = Join-Path $work 'Files.v3.wxs'
$prodV4  = Join-Path $work 'Product.v4.wxs'

$dirMap = @{}
function Get-DirId([string]$path) {
  if ([string]::IsNullOrEmpty($path)) { return 'INSTALLDIR' }
  if ($path -eq $dist) { return 'INSTALLDIR' }
  if ($dirMap.ContainsKey($path)) { return $dirMap[$path].Id }
  $name = Split-Path $path -Leaf
  $hash = [BitConverter]::ToString([System.Security.Cryptography.SHA1]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($path))).Replace('-', [string]::Empty).Substring(0,8)
  $id = 'DIR_' + $hash
  # store as PSCustomObject for dot-property access
  $dirMap[$path] = [PSCustomObject]@{ Id=$id; Name=$name; Parent=(Split-Path $path -Parent) }
  return $id
}

# Generate a stable GUID from input string (MD5-based, formatted as 8-4-4-4-12)
function New-StableGuidFromString([string]$text) {
  $bytes = [Text.Encoding]::UTF8.GetBytes($text)
  $md5 = [System.Security.Cryptography.MD5]::Create().ComputeHash($bytes)
  $hex = ([BitConverter]::ToString($md5)).Replace('-', '').ToUpperInvariant()
  $g = (
    $hex.Substring(0,8) + '-' +
    $hex.Substring(8,4) + '-' +
    $hex.Substring(12,4) + '-' +
    $hex.Substring(16,4) + '-' +
    $hex.Substring(20,12)
  )
  return '{' + $g + '}'
}

$components = @()
$directories = New-Object System.Collections.Generic.HashSet[string]
$directories.Add($dist) | Out-Null

Get-ChildItem -Path $dist -Recurse -File | ForEach-Object {
  $filePath = $_.FullName
  $fileDir  = Split-Path $filePath -Parent
  $cur = $fileDir
  while ($cur -and ($cur.ToLower().StartsWith($dist.ToString().ToLower()))) {
    if (-not $directories.Contains($cur)) { $directories.Add($cur) | Out-Null }
    if ($cur -eq $dist) { break }
    $cur = Split-Path $cur -Parent
  }
  $rel = (Resolve-Path -LiteralPath $filePath).Path
  $hash = [BitConverter]::ToString([System.Security.Cryptography.SHA1]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes([string]$rel))).Replace('-', [string]::Empty).Substring(0,12)
  $cmpId = 'CMP_' + $hash
  $fileId = 'FIL_' + $hash
  $dirId = Get-DirId $fileDir
  $components += [PSCustomObject]@{ Id=$cmpId; FileId=$fileId; DirId=$dirId; Source=$rel }
}

# Build v3 fragment via XmlDocument to avoid special chars in script
$xml = New-Object System.Xml.XmlDocument
$decl = $xml.CreateXmlDeclaration('1.0','UTF-8',$null)
$null = $xml.AppendChild($decl)

$wix = $xml.CreateElement('Wix')
$null = $wix.SetAttribute('xmlns','http://schemas.microsoft.com/wix/2006/wi')
$null = $xml.AppendChild($wix)

# Fragment 1: declare directories (nested under INSTALLDIR to preserve hierarchy)
$frag1 = $xml.CreateElement('Fragment')
$null = $wix.AppendChild($frag1)
$dirRef1 = $xml.CreateElement('DirectoryRef')
$null = $dirRef1.SetAttribute('Id','INSTALLDIR')
$null = $frag1.AppendChild($dirRef1)

# Build a nested directory tree so that e.g. INSTALLDIR\_internal\PyQt6\Qt6\plugins\platforms is preserved
# Map: fullPath -> corresponding Directory XmlElement (parent for children)
$dirNodes = @{}
$dirNodes[$dist] = $dirRef1

# Order directories by depth to ensure parents are created before children
$orderedDirs = $directories |
  Where-Object { $_ -ne $dist } |
  Sort-Object {
    $rel = $_.Substring($dist.Length)
    # remove any leading path separators in relative part
    $rel = [Regex]::Replace($rel, '^[\\/]+', '')
    # count non-empty segments to get depth
    (($rel -split '[\\/]' | Where-Object { $_ -ne '' }).Count)
  }

foreach ($d in $orderedDirs) {
  $entry = $dirMap[$d]
  if (-not $entry) { $null = Get-DirId $d; $entry = $dirMap[$d] }

  $parentPath = Split-Path $d -Parent
  if ([string]::IsNullOrEmpty($parentPath)) { $parentPath = $dist }
  if (-not $dirNodes.ContainsKey($parentPath)) {
    # Fallback: ensure parent is registered (should exist due to depth ordering)
    $null = Get-DirId $parentPath
    if ($parentPath -eq $dist) { $dirNodes[$parentPath] = $dirRef1 }
  }

  $parentNode = $dirNodes[$parentPath]
  if (-not $parentNode) { $parentNode = $dirRef1 }

  $dir = $xml.CreateElement('Directory')
  $null = $dir.SetAttribute('Id', $entry.Id)
  $null = $dir.SetAttribute('Name', $entry.Name)
  $null = $parentNode.AppendChild($dir)
  $dirNodes[$d] = $dir
}

# Fragment 2: file components under INSTALLDIR, pointing to each Directory
$frag2 = $xml.CreateElement('Fragment')
$null = $wix.AppendChild($frag2)
$dirRef2 = $xml.CreateElement('DirectoryRef')
$null = $dirRef2.SetAttribute('Id','INSTALLDIR')
$null = $frag2.AppendChild($dirRef2)

foreach ($c in $components) {
  $comp = $xml.CreateElement('Component')
  $null = $comp.SetAttribute('Id', $c.Id)
  # Use deterministic per-file GUID for component to avoid duplicates and ensure stability across builds
  $stableGuid = New-StableGuidFromString([string]$c.Source)
  $null = $comp.SetAttribute('Guid', $stableGuid)
  $null = $comp.SetAttribute('Directory', $c.DirId)

  $file = $xml.CreateElement('File')
  $null = $file.SetAttribute('Id', [string]$c.FileId)
  $null = $file.SetAttribute('Source', [string]$c.Source)
  $null = $file.SetAttribute('KeyPath', 'yes')
  $null = $comp.AppendChild($file)

  $null = $dirRef2.AppendChild($comp)
}

# Fragment 3: component group
$frag3 = $xml.CreateElement('Fragment')
$null = $wix.AppendChild($frag3)
$group = $xml.CreateElement('ComponentGroup')
$null = $group.SetAttribute('Id','AppFiles')
$null = $frag3.AppendChild($group)
foreach ($c in $components) {
  $ref = $xml.CreateElement('ComponentRef')
  $null = $ref.SetAttribute('Id', $c.Id)
  $null = $group.AppendChild($ref)
}

$xml.Save($filesV3)

Copy-Item (Join-Path $scriptDir 'Product.wxs') $prodV4 -Force
wix extension add WixToolset.UI.wixext --global | Out-Null
wix extension add WixToolset.Util.wixext --global | Out-Null

$sources = @($prodV4, $filesV3)
wix convert @sources | Out-Null

# Log sources to build
Write-Host 'Sources to build:'
$sources | ForEach-Object { Write-Host ('  ' + $_) }

$locFile = Join-Path $scriptDir ("Strings.$Culture.wxl")
if (-not (Test-Path $locFile)) {
  Write-Host ("Localization file not found for culture {0}, falling back to zh-CN" -f $Culture) -ForegroundColor Yellow
  $Culture = 'zh-CN'
  $locFile = Join-Path $scriptDir ("Strings.$Culture.wxl")
}

$msiName = ('PracticeApp-' + $Version + '-' + $Culture + '.msi')
$msiOut = Join-Path $scriptDir $msiName
wix build -ext WixToolset.UI.wixext -ext WixToolset.Util.wixext -d DistDir=$dist -o $msiOut -culture $Culture -loc $locFile @sources
if ($LASTEXITCODE -ne 0) {
  Write-Error ('wix build failed, exit code {0}' -f $LASTEXITCODE)
  exit $LASTEXITCODE
}

Write-Host ('MSI generated: {0}' -f $msiOut) -ForegroundColor Green