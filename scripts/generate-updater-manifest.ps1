param(
    [Parameter(Mandatory = $true)]
    [string]$Version,

    [Parameter(Mandatory = $true)]
    [string]$AssetPath,

    [Parameter(Mandatory = $true)]
    [string]$DownloadUrl,

    [string]$OutputPath = "",
    [string]$Platform = "windows-x86_64",
    [string]$Notes = "",
    [string]$PubDate = ""
)

if (-not (Test-Path $AssetPath)) {
    throw "Asset not found: $AssetPath"
}

$signaturePath = "$AssetPath.sig"
if (-not (Test-Path $signaturePath)) {
    throw "Signature not found: $signaturePath"
}

if (-not $OutputPath) {
    $OutputPath = Join-Path (Split-Path $AssetPath -Parent) "latest.json"
}

if (-not $PubDate) {
    $PubDate = (Get-Date).ToUniversalTime().ToString("o")
}

$signature = (Get-Content $signaturePath -Raw).Trim()

$manifest = [ordered]@{
    version = $Version
    notes = $Notes
    pub_date = $PubDate
    platforms = [ordered]@{
        $Platform = [ordered]@{
            signature = $signature
            url = $DownloadUrl
        }
    }
}

$json = $manifest | ConvertTo-Json -Depth 5
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($OutputPath, $json + [Environment]::NewLine, $utf8NoBom)

Write-Output "Generated updater manifest: $OutputPath"